# Development

## Contribution source of truth

[CONTRIBUTING](https://github.com/embeddedos-org/eCAD-Hardware-Products/blob/master/CONTRIBUTING.md)

Before proposing a change, also review the [README](https://github.com/embeddedos-org/eCAD-Hardware-Products/blob/master/README.md). Keep changes scoped, add tests appropriate to the affected behavior, and follow the repository's current automation and review requirements.

## Build and dependency inputs found

`eRadar360_CAD_Design/mobile/flutter_app/windows/runner/CMakeLists.txt`, `eRadar360_CAD_Design/mobile/react_native_app/package.json`, `tools/requirements.txt`.

## Tests found in the default-branch tree

`eRadar360_CAD_Design/mobile/flutter_app/test/app_test.dart`, `eRadar360_CAD_Design/mobile/flutter_app/test/domain_test.dart`, `eRadar360_CAD_Design/mobile/react_native_app/__tests__/accessibility.test.ts`, `eRadar360_CAD_Design/mobile/react_native_app/__tests__/api.test.ts`, `eRadar360_CAD_Design/mobile/react_native_app/__tests__/domain.test.ts`, `eRadar360_CAD_Design/mobile/react_native_app/__tests__/ios_android.test.ts`, `eRadar360_CAD_Design/mobile/react_native_app/__tests__/navigation.test.tsx`, `eRadar360_CAD_Design/mobile/react_native_app/__tests__/performance.test.ts`, `eRadar360_CAD_Design/mobile/react_native_app/__tests__/platform.test.ts`, `eRadar360_CAD_Design/mobile/react_native_app/__tests__/ui.test.tsx`, `eRadar360_CAD_Design/simulation/factory_test/eradar360_factory_test.py`, `eRadar360_CAD_Design/tests/e2e.test.ts`, and 15 more.

## Documented test commands

These commands are reproduced from the inspected root README or contributing guide:

```bash
cmake -B build
```

```bash
cmake --build build
```

```bash
ctest --test-dir build --output-on-failure
```

## Verification baseline

This inventory comes from `master` at [`348270767720`](https://github.com/embeddedos-org/eCAD-Hardware-Products/commit/348270767720ba989ff58c8ccf2bbbc2c934a67e) and found 27 test-related paths among 1226 files. Re-check the source tree when that commit is no longer current.
