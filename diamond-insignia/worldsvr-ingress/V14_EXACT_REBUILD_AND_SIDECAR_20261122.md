# v291 Diamond: source-exact v14 reconstruction and ABI-preserving ELF interposition (2026-11-22)

## Deterministic reproduction of running v14 lib.so

**Breakthrough:** From user's `CABAL_V282_SOURCE_v14.tar.gz`, building the **unchanged** `source_tree/src` in the correct explicit ordered list with:

```sh
g++ -std=c++17 -O2 -fPIC -shared -Wl,-soname,lib.so -Wl,-rpath,/usr/lib/cabal -o lib.so ${ordered_cpp_files[@]} -ldl -lpthread -lodbc
```

produces an exact **bit-for-bit SHA256 match** to the actual running `/usr/lib/cabal/lib.so`:

```
EXPECTED=6679e46aa2ee915d97de9501ba027cae3eec153f1cd82e7c16ed47221c63ecab
ACTUAL=6679e46aa2ee915d97de9501ba027cae3eec153f1cd82e7c16ed47221c63ecab
ORIGINAL_V14_EXACT=PASS
```

The ordered source-file list / reproducible build script are in the user's conversation artifact `CABAL_V291_Diamond_Sidecar_ReadOnly_20261122.zip`, file `rebuild-original-v14-exact.sh`. The private original v14 sources are **not uploaded to GitHub**.

Older rebuilt candidates did **not** preserve internal function RVAs. Unpatched rebuild with a different source linker order gave original `ProcSystem::DoProcessDataCtx` RVA `0x68e0` vs rebuilt `0x5f10`. Even after exact source file order, adding Diamond directly to ProcSystem changes at least 109 exported function RVAs, because of the increased function size and optimizer reordering. This may upset existing plugins or ABI / hardcoded pointers; **not a proven root cause of Supervisor exit 78**. Both prior plugin replacement attempts failed and correctly rolled back.

## Read-only sidecar instead of replacing original lib.so

ELF static disassembly of original `ProcSystem::Attach` reveals `mov rdx,[rip+...] ` reading **R_X86_64_GLOB_DAT** GOT relocation at original `lib.so` RVA **0x16f78**, symbol:

`_ZN10ProcSystem16DoProcessDataCtxEPvP18PROCESSDATACONTEXT`.

Therefore a separate `libdiamond_v291_sidecar.so` loaded **before** original `lib.so` can symbol-interpose the handler while preserving the *entire* original active binary and its layout. Sidecar exported same symbol and delegates by `dlsym(RTLD_NEXT,...) `. In this first passive stage, records only sanitized C2S packet opcode 0x09F3/0x0B10 and length/Mastery ID, limited to first 32, behind environment `CABAL_DIAMOND_SIDECAR_LOG=1`, then calls original handler unchanged. No account/inventory/SQL/WExp changes.

**Offline tests performed and PASS:**

1. Real original v14 `lib.so` `dlopen` with sidecar `LD_PRELOAD`: GOT RVA `0x16f78` resolves to sidecar function, **not** original: `LIBSO_SYMBOL_PREEMPTION=PASS`.
2. Synthetic mock-WorldSvr dispatch: 0x09F3, 0x0B10 and malformed packet all forwarded, original return 12345 preserved. Log captured only 0x09F3 Mastery id=159 and 0x0B10 packet length, with `passthrough=YES`.
3. New library only 16,296B, `libdiamond_v291_sidecar.so` SHA256 `2118cebb63de7a88f1eb666dc2d379d602fd66625f706e2298f36339ceb6115e`. Package ZIP `CABAL_V291_Diamond_Sidecar_ReadOnly_20261122.zip` SHA256 `861f67d42107363de2cfdf36f37ad2c7237bdb0d7b80e4cd3eada95a234e5277`.

**Not yet installed/tested** on owner's VM. Actual VM `LD_PRELOAD`/supervisor env and plugin ordering must be inspected first. No install instructions should modify live `lib.so`. A full rollback script for the service launch configuration and isolated snapshot is needed before a VM test.

**Still NOT complete Diamond gameplay** — authoritative item 33554961/WExp debit, real SQL transaction, S2C serialization and client state remain unimplemented.
