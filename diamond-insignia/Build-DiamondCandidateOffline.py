#!/usr/bin/env python3
"""Compile the Diamond source candidate and run checks without a game server."""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
UNITS = [
    'worldsvr-ingress/DiamondNativeRankUpCompletion.cpp',
    'native/grade2-ingress/DiamondWorld48TicketUnits.cpp',
    'native/world-session-bridge/deps/EventPassOwnerV282.cpp',
    'native/inventory-reconcile/DiamondInventoryReconcile.cpp',
    'native/grade2-ingress/DiamondGradeUp0BDA.cpp',
    'native/grade2-ingress/Diamond0BDATicketSelection.cpp',
    'native/grade2-ingress/Diamond0BDAGameplayAction.cpp',
    'native/grade2-ingress/Diamond0BDAAuthenticatedIngress.cpp',
    'native/real-gamedata-transaction/DiamondRealGameDataOdbc.cpp',
    'native/real-gamedata-transaction/Diamond0BDARealServer01Bridge.cpp',
    'native/world-save-barrier/DiamondWorldSaveBarrier.cpp',
    'native/grade2-ingress/Diamond0BDASaveReplyGate.cpp',
]
ENTRY = '''#include "worldsvr-ingress/DiamondNativeRankUpV20.h"
extern "C" unsigned cabal_diamond_native_abi() noexcept {
    return diamond_v20::kCompletionHostAbi;
}
extern "C" int cabal_diamond_native_register(
    const diamond_v19::Host* host, const diamond_v20::Binding* binding) noexcept {
    if(!host || !binding)return static_cast<int>(diamond_v19::Status::Blocked);
    return static_cast<int>(diamond_v20::Register(*host,*binding));
}
'''


def run(args):
    subprocess.run([str(a) for a in args], check=True, timeout=120, cwd=ROOT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--cxx', default='g++')
    parser.add_argument('--odbc-include', action='append', default=[])
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    entry = out/'entry.cpp'
    entry.write_text(ENTRY, encoding='utf-8')
    flags = [args.cxx, '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
             '-pedantic', '-I'+str(ROOT)]
    flags += ['-I'+str(Path(p).resolve()) for p in args.odbc_include]
    sources = [ROOT/p for p in UNITS]
    modules = []
    for name, defines in [('default', []),
                          ('clone', ['-DDIAMOND_ENABLE_0BDA_CLONE_TRIAL'])]:
        module = out/('DiamondCandidate-'+name+'.so')
        run(flags+defines+['-fPIC', '-shared', '-Wl,-z,defs', entry,
                          *sources, '-l:libodbc.so.2', '-o', module])
        library = ctypes.CDLL(str(module))
        library.cabal_diamond_native_abi.restype = ctypes.c_uint
        library.cabal_diamond_native_register.argtypes = [ctypes.c_void_p]*2
        assert library.cabal_diamond_native_abi() == 0x20261129
        assert library.cabal_diamond_native_register(None, None) == 0
        modules.append({'file': module.name,
                        'sha256': hashlib.sha256(module.read_bytes()).hexdigest()})
    barrier = [ROOT/UNITS[i] for i in (0, 10, 11)]
    for name in ('test_native_rankup_v20', 'test_native_rankup_completion'):
        executable = out/name
        run(flags+['-DDIAMOND_ENABLE_0BDA_CLONE_TRIAL',
                   ROOT/'worldsvr-ingress'/(name+'.cpp'), *barrier,
                   '-o', executable])
        run([executable])
    # The real ODBC implementation is linked, while the disabled host test
    # rejects the request before any connection to a database is attempted.
    executable = out/'test_real_server01_dispatch_chain'
    run(flags+[ROOT/'native/real-gamedata-transaction/test_real_server01_dispatch_chain.cpp',
               *sources, '-l:libodbc.so.2', '-o', executable])
    run([executable])
    report = {'status': 'OFFLINE_BUILD_AND_CHECKS_PASS', 'modules': modules,
              'installation_ready': False, 'native_session_provider_present': False,
              'native_save_routes_connected': False, 'live_sql_executed': False,
              'server_restarted': False}
    (out/'BUILD-REPORT.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
