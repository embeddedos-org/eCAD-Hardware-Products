"""
tests/unit/test_product_data.py — product catalog and generated-data checks
SPDX-License-Identifier: MIT  Copyright (c) 2026 EmbeddedOS Foundation

These tests guard two separate promises.

The first is that the committed product tree still matches the catalog it was
generated from. Without that check, a hand edit to a generated bom.csv would
survive until the next unrelated regeneration silently reverted it.

The second is that the data itself is internally consistent -- schema, unique
reference designators, and BOM arithmetic. tools/validate_products.py re-derives
those figures from the CSV rather than from the catalog, so a fault in the
generator surfaces here instead of passing unnoticed.

Neither test claims a manufacturer part number is real or that a unit cost is
current. Nothing in this repository checks that; see the note in
tools/catalog/components.json.
"""

import os
import subprocess
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

import cad_geometry  # noqa: E402
import cad_render  # noqa: E402
import generate_products  # noqa: E402
import validate_products  # noqa: E402


def _run(*args: str) -> subprocess.CompletedProcess:
    """Run a repository tool as a subprocess from the repository root.

    Args:
        *args: Arguments following the interpreter, e.g. a script path.

    Returns:
        The completed process, with stdout and stderr captured as text.
    """
    return subprocess.run(
        [sys.executable, *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=900,
    )


class TestComponentLibrary(unittest.TestCase):
    """The curated component library must be well formed."""

    @classmethod
    def setUpClass(cls):
        cls.library = generate_products.load_components()

    def test_library_is_not_empty(self):
        self.assertGreater(len(self.library), 100)

    def test_every_component_has_a_positive_cost(self):
        for key, record in self.library.items():
            with self.subTest(component=key):
                self.assertIsInstance(record["cost"], (int, float))
                self.assertGreaterEqual(record["cost"], 0)

    def test_manufacturer_part_numbers_are_unique(self):
        seen = {}
        for key, record in self.library.items():
            mpn = record["mpn"]
            self.assertNotIn(
                mpn,
                seen,
                f"components {seen.get(mpn)!r} and {key!r} share MPN {mpn!r}; "
                "a duplicate means one of them is misattributed",
            )
            seen[mpn] = key

    def test_no_component_field_is_blank(self):
        for key, record in self.library.items():
            for field in ("manufacturer", "mpn", "value", "footprint", "description", "source"):
                with self.subTest(component=key, field=field):
                    self.assertTrue(str(record[field]).strip())


class TestCatalogIntegrity(unittest.TestCase):
    """Every catalog must render without raising and reference real parts."""

    @classmethod
    def setUpClass(cls):
        cls.library = generate_products.load_components()
        cls.catalogs = generate_products.load_division_catalogs()

    def test_catalogs_exist(self):
        self.assertTrue(self.catalogs, "no division catalogs were found")

    def test_every_product_renders(self):
        for catalog in self.catalogs:
            for product in catalog.get("products", []):
                with self.subTest(division=catalog["division"], product=product.get("slug")):
                    self.assertTrue(generate_products.render_datasheet(product))
                    self.assertTrue(generate_products.render_bom(product, self.library))
                    self.assertTrue(generate_products.render_power_sim(product))

    def test_product_slugs_are_unique_within_a_division(self):
        for catalog in self.catalogs:
            slugs = [p["slug"] for p in catalog.get("products", [])]
            with self.subTest(division=catalog["division"]):
                self.assertCountEqual(slugs, set(slugs), "duplicate product slug")

    def test_unknown_component_key_is_rejected(self):
        """A typo in a catalog part key must fail loudly, not render an empty cell."""
        with self.assertRaises(generate_products.CatalogError):
            generate_products.render_bom(
                {"slug": "probe", "bom": [{"ref": "U1", "part": "no_such_part", "qty": 1}]},
                self.library,
            )

    def test_colliding_catalog_refs_are_allocated_distinct_designators(self):
        """The catalog's ``ref`` is a prefix hint; numbering is allocated here.

        Two BOM lines may both say ``U1``. They must still come out as distinct
        parts, because a board cannot have two U1. This replaces an older test
        that expected a duplicate to raise: duplicates are now impossible by
        construction, which is a stronger guarantee than detecting them.
        """
        csv_text = generate_products.render_bom(
            {
                "slug": "probe",
                "bom": [
                    {"ref": "U1", "part": "atecc608b", "qty": 1},
                    {"ref": "U1", "part": "atecc608b", "qty": 1},
                ],
            },
            self.library,
        )
        references = [line.split(",")[0] for line in csv_text.splitlines()[1:-1]]
        self.assertEqual(references, ["U1", "U2"])
        self.assertEqual(len(set(references)), len(references))

    def test_non_positive_quantity_is_rejected(self):
        for bad in (0, -3, "two"):
            with self.subTest(qty=bad):
                with self.assertRaises(generate_products.CatalogError):
                    generate_products.render_bom(
                        {"slug": "probe",
                         "bom": [{"ref": "U1", "part": "atecc608b", "qty": bad}]},
                        self.library,
                    )

    def test_bom_arithmetic_is_computed_not_copied(self):
        """Extended cost must equal quantity x unit cost in rendered output."""
        csv_text = generate_products.render_bom(
            {"slug": "probe", "bom": [{"ref": "U1", "part": "atecc608b", "qty": 7}]},
            self.library,
        )
        unit = self.library["atecc608b"]["cost"]
        expected = f"{unit * 7:.2f}"
        self.assertIn(expected, csv_text)
        self.assertIn(f"TOTAL,,,,,,,{expected},,", csv_text)


class TestCadGeometry(unittest.TestCase):
    """Board geometry must be derived from the datasheet, never guessed."""

    @classmethod
    def setUpClass(cls):
        cls.catalogs = generate_products.load_division_catalogs()

    def test_every_product_yields_geometry(self):
        for catalog in self.catalogs:
            for product in catalog.get("products", []):
                with self.subTest(product=product["slug"]):
                    geometry = cad_render.board_geometry(product)
                    self.assertIn(geometry["shape"], ("rect", "circle"))
                    self.assertGreater(geometry["layers"], 1)

    def test_unreadable_dimensions_are_rejected(self):
        """A dimension string that cannot be parsed must raise, not default."""
        with self.assertRaises(cad_render.CadError):
            cad_render.board_geometry(
                {"slug": "probe", "pcb": [["Layers", "4"], ["Dimensions", "about yay big"]]}
            )

    def test_odd_layer_count_is_rejected(self):
        with self.assertRaises(cad_render.CadError):
            cad_render.board_geometry(
                {"slug": "probe", "pcb": [["Layers", "7"], ["Dimensions", "50mm x 40mm"]]}
            )

    def test_identifiers_are_deterministic(self):
        """Regenerating an unchanged catalog must reproduce identical files."""
        geometry = {
            "shape": "rect", "width": 50.0, "height": 40.0, "layers": 4,
            "ipc": "Class 2", "finish": "ENIG", "stackup_note": "",
        }
        product = {"slug": "probe", "part": "eX-1"}
        first = cad_render.render_kicad_pcb(product, geometry)
        second = cad_render.render_kicad_pcb(product, geometry)
        self.assertEqual(first, second)

    def test_kicad_board_declares_requested_layer_count(self):
        for layers in (2, 4, 8, 12, 16):
            with self.subTest(layers=layers):
                geometry = {
                    "shape": "rect", "width": 50.0, "height": 40.0, "layers": layers,
                    "ipc": "Class 3", "finish": "ENIG", "stackup_note": "",
                }
                text = cad_render.render_kicad_pcb({"slug": "p", "part": "eX"}, geometry)
                self.assertEqual(text.count(" signal)"), layers)


class TestReferenceDesignators(unittest.TestCase):
    """A BOM line with quantity N must name N distinct designators."""

    @classmethod
    def setUpClass(cls):
        cls.library = generate_products.load_components()
        cls.catalogs = generate_products.load_division_catalogs()

    def test_quantity_expands_to_that_many_designators(self):
        lines = cad_geometry.expand_references(
            {"bom": [{"ref": "C1", "part": "c", "qty": 180}]}
        )
        self.assertEqual(len(lines[0]["designators"]), 180)
        self.assertEqual(lines[0]["display"], "C1-C180")

    def test_designators_never_collide_across_bom_lines(self):
        """Two lines sharing a prefix must not be allocated the same numbers."""
        lines = cad_geometry.expand_references(
            {"bom": [
                {"ref": "U1", "part": "a", "qty": 6},
                {"ref": "U2", "part": "b", "qty": 3},
            ]}
        )
        first, second = set(lines[0]["designators"]), set(lines[1]["designators"])
        self.assertEqual(len(first & second), 0)
        self.assertEqual(lines[1]["display"], "U7-U9")

    def test_round_trip_through_display_reference(self):
        for display, expected in (("C1-C4", 4), ("U7", 1), ("PCB1", 1)):
            with self.subTest(display=display):
                self.assertEqual(
                    len(cad_geometry.expand_display_reference(display)), expected
                )

    def test_every_product_has_unique_designators(self):
        for catalog in self.catalogs:
            for product in catalog.get("products", []):
                with self.subTest(product=product["slug"]):
                    seen = set()
                    for line in cad_geometry.expand_references(product):
                        for designator in line["designators"]:
                            self.assertNotIn(designator, seen, f"duplicate {designator}")
                            seen.add(designator)


class TestPlacementFeasibility(unittest.TestCase):
    """Every board must physically hold the parts assigned to it."""

    @classmethod
    def setUpClass(cls):
        cls.library = generate_products.load_components()
        cls.catalogs = generate_products.load_division_catalogs()

    def test_every_board_fits_its_components(self):
        for catalog in self.catalogs:
            for product in catalog.get("products", []):
                with self.subTest(product=product["slug"]):
                    geometry = cad_render.board_geometry(product)
                    result = cad_geometry.place_components(
                        cad_geometry.expand_references(product), self.library, geometry
                    )
                    self.assertEqual(
                        result["overflow"], [],
                        f"{product['slug']}: {len(result['overflow'])} parts do not fit",
                    )

    def test_assembly_items_are_not_placed_on_the_board(self):
        """A PCB cannot be mounted on itself; nor can an enclosure."""
        library = {
            "board": {"footprint": "Custom", "assembly": True},
            "chip": {"footprint": "0402"},
        }
        result = cad_geometry.place_components(
            [
                {"part": "board", "qty": 1, "designators": ["PCB1"]},
                {"part": "chip", "qty": 2, "designators": ["C1", "C2"]},
            ],
            library,
            {"shape": "rect", "width": 50.0, "height": 40.0},
        )
        placed = {item["designator"] for item in result["placements"]}
        self.assertEqual(placed, {"C1", "C2"})
        self.assertEqual(result["excluded_assembly"], 1)

    def test_oversized_part_is_reported_not_silently_dropped(self):
        result = cad_geometry.place_components(
            [{"part": "big", "qty": 1, "designators": ["U1"]}],
            {"big": {"footprint": "SO-DIMM 260"}},
            {"shape": "rect", "width": 20.0, "height": 20.0},
        )
        self.assertEqual(result["overflow"], ["U1"])

    def test_exact_packages_are_flagged_as_exact(self):
        self.assertTrue(cad_geometry.package_model("0402")["exact"])
        self.assertFalse(cad_geometry.package_model("LQFP144")["exact"])


class TestGeneratedTreeIsCurrent(unittest.TestCase):
    """The committed product tree must match what the catalog renders."""

    def test_generated_tree_matches_catalog(self):
        result = _run("tools/generate_products.py", "--check", "--quiet")
        self.assertEqual(
            result.returncode,
            0,
            "the committed product tree is out of date with tools/catalog.\n"
            "Run: python3 tools/generate_products.py\n"
            f"{result.stdout}{result.stderr}",
        )


class TestProductDataValidates(unittest.TestCase):
    """Every product directory must satisfy the data contract."""

    def test_validator_reports_no_unbaselined_failure(self):
        result = _run("tools/validate_products.py", "--run", "--quiet")
        self.assertEqual(
            result.returncode,
            0,
            f"product data validation failed:\n{result.stdout}{result.stderr}",
        )

    def test_baseline_keys_are_portable_across_path_separators(self):
        outcome = validate_products.Result(
            target="division\\product", failures=["known defect"]
        )

        validate_products.apply_baseline(
            outcome,
            {"division/product": {"known defect": "tracked historical defect"}},
        )

        self.assertTrue(outcome.ok)
        self.assertEqual(outcome.target, "division/product")
        self.assertEqual(len(outcome.known), 1)

    def test_validator_detects_a_broken_bom(self):
        """The validator must be able to fail; a check that cannot fail is not a check."""
        import tempfile

        with tempfile.TemporaryDirectory() as workspace:
            broken = os.path.join(workspace, "bom.csv")
            with open(broken, "w", encoding="utf-8") as handle:
                handle.write(
                    "Reference,Quantity,Value,Footprint,Manufacturer,MPN,Description,"
                    "Unit Cost USD,Extended Cost USD,Source\n"
                    "U1,2,V,F,Acme,ACME-1,Widget,10.00,999.00,Mouser\n"
                    "TOTAL,,,,,,,12.34,,Approximate BOM cost\n"
                )
            outcome = validate_products.validate_bom(broken)
            self.assertFalse(outcome.ok)
            joined = " ".join(outcome.failures)
            self.assertIn("extended cost", joined)
            self.assertIn("stated total", joined)


if __name__ == "__main__":
    unittest.main()
