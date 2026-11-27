# Test the actual procedure body using only connection-local #temporary data.
# No game rows, persistent objects, installation or service changes.
[CmdletBinding()]
param([string]$SshTarget='root@192.168.56.101')
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
$base='https://raw.githubusercontent.com/patmalnieksgatis-netizen/CABAL-Downloads/d0428456795a5b24190af053f642b0e035d4d3bf/diamond-insignia/native/real-gamedata-transaction/'
$files=@(
    @{Name='test_rankup_in_temp_tables.py';Sha='42a04c5e0586428a31416377a01cba1217df13e2e9c21cb245aafb040b0af64f'},
    @{Name='00_server01_clone_atomic_rankup_v291.sql';Sha='1dc000673da9e5e53af7192061b8ba5d7adef8b4b7dc405758e5550f15e46d45'}
)
$work=Join-Path $env:TEMP ('Diamond-TempSql-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $work | Out-Null
try {
    foreach($file in $files){
        $path=Join-Path $work $file.Name
        Invoke-WebRequest -UseBasicParsing -Uri ($base+$file.Name) -OutFile $path -ErrorAction Stop
        if((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $file.Sha){
            throw 'DIAMOND_TEST_SOURCE_HASH_DIFFERS'
        }
    }
    $python=[IO.File]::ReadAllText((Join-Path $work $files[0].Name))
    $sql=[IO.File]::ReadAllBytes((Join-Path $work $files[1].Name))
    $encoded=[Convert]::ToBase64String($sql)
    $source="SOURCE_SQL=__import__('base64').b64decode('$encoded')`n$python"
    Write-Host 'DIAMOND: SQL_DZINEJA_TESTS_PAGAIDU_TABULAS; SPELES_DATI_NETIEK_MAINITI'
    Write-Host 'SPELI_VAR_ATSTAT_ATVERTU; NEKAS_NETIEK_PARSTARTETS'
    $savedEncoding=$OutputEncoding
    try {
        $OutputEncoding=New-Object System.Text.UTF8Encoding($false)
        $lines=@($source | & ssh.exe -T -o ConnectTimeout=12 $SshTarget 'python3 -')
        $code=$LASTEXITCODE
    } finally {$OutputEncoding=$savedEncoding}
    $lines | ForEach-Object {Write-Host $_}
    if($code -ne 0 -or $lines -notcontains 'DIAMOND_TEMP_SQL_TEST=PASS'){
        throw 'DIAMOND_TEMP_SQL_NAV_APSTIPRINATS; ATSUTI_IZVADI'
    }
    Write-Host 'SQL_TESTS_PABEIGTS; WORLD_DIAMOND_VEL_NAV_AKTIVIZETS'
} finally {
    Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
}
