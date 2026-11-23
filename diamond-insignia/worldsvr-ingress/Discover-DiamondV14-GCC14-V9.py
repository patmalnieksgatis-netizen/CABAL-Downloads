#!/usr/bin/env python3
"""CABAL Diamond V9: read-only discovery of available GCC 14.2 toolchains.

No apt, image pull, container creation, source writes, service restart, or SQL calls.
"""
import json
import pathlib
import shutil
import subprocess

def command(argv, timeout=12):
    try:
        p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                         text=True,timeout=timeout,check=False)
        return {"exit_code":p.returncode,"stdout":p.stdout.strip()[:2000],
                "stderr":p.stderr.strip()[:500]}
    except (OSError,subprocess.TimeoutExpired) as e:
        return {"error":str(e)[:500]}

def main():
    result={"status":"V9_READ_ONLY_TOOLCHAIN_DISCOVERY",
            "install_allowed":False,"changes_made":False,
            "local_compilers":{},"docker":{}}
    for name in ("g++-14","gcc-14","g++","gcc","clang++","docker","podman"):
        path=shutil.which(name)
        result["local_compilers"][name]={"path":path}
        if path and name not in ("docker","podman"):
            result["local_compilers"][name]["version"]=command([path,"-dumpfullversion","-dumpversion"])
    docker=shutil.which("docker")
    if docker:
        result["docker"]["containers"]=command([docker,"ps","--format","{{.Names}}"])
        result["docker"]["images"]=command([docker,"images","--format","{{.Repository}}:{{.Tag}} {{.ID}}"])
        for name in ("cabal_main","sql_main"):
            probe=command([docker,"inspect","--type=container","--format","{{.State.Running}}",name])
            result["docker"][name]={"state":probe}
            if probe.get("stdout")=="true":
                result["docker"][name]["gcc"]=command([docker,"exec",name,"gcc","-dumpfullversion","-dumpversion"])
                result["docker"][name]["g++"]=command([docker,"exec",name,"g++","-dumpfullversion","-dumpversion"])
                # Read-only: search for SQL development headers without starting services.
                result["docker"][name]["sql_header"]=command([docker,"exec",name,"test","-f","/usr/include/sql.h"])
    print("BEGIN_DIAMOND_V9_TOOLCHAIN_DISCOVERY")
    print(json.dumps(result,indent=2,sort_keys=True))
    print("END_DIAMOND_V9_TOOLCHAIN_DISCOVERY")

if __name__=="__main__":
    main()
