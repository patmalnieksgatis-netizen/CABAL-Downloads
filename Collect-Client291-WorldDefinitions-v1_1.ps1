param([ValidateSet('Inspect','Collect')][string]$Action='Inspect')
$ErrorActionPreference='Stop'
$root='F:\CABAL_291_TEST'
if($Action -eq 'Inspect') {
    [ordered]@{Action='READ_ONLY_DEFINITION_COPY';ClientRoot=$root;VM='192.168.56.101';Container='cabal_main';Required='Data\quest.enc';Optional=@('Data\AnimaMastery.enc','Data\pet.enc');NativeFile='/etc/cabal/Data/Quest.scp';GameStarted=$false;Installation=$false;SQL=$false;CredentialsExported=$false;LoadedCounts='Only three public definition counts per Quest.scp ID; pinned World hash required'} | ConvertTo-Json
    return
}
if($env:OS -ne 'Windows_NT'){throw 'USE_WINDOWS_POWERSHELL'}
$main=Join-Path $root 'Bin\x64\CabalMain.exe'
if((Get-FileHash -LiteralPath $main -Algorithm SHA256).Hash -ne '52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9'){throw 'CLIENT_291_PROFILE_DIFFERS'}
$data=Join-Path $root 'Data'
if(!(Test-Path -LiteralPath (Join-Path $data 'quest.enc') -PathType Leaf)){throw 'NAV_CLIENT291_DATA_QUEST_ENC'}
$downloads=Join-Path $env:USERPROFILE 'Downloads'
$name='Client291-WorldDefinitions-'+(Get-Date -Format yyyyMMdd-HHmmss)+'-'+[guid]::NewGuid().ToString('N').Substring(0,6)
$folder=Join-Path $downloads $name
[void](New-Item -ItemType Directory -Path $folder)
$files=@()
foreach($file in @('quest.enc','AnimaMastery.enc','pet.enc')) {
    $source=Join-Path $data $file
    if(!(Test-Path -LiteralPath $source -PathType Leaf)){continue}
    $item=Get-Item -LiteralPath $source
    if($item.Length -le 0 -or $item.Length -gt 8MB){throw ('CLIENT_DATA_FILE_EXTENT='+$file)}
    $destination=Join-Path $folder $file
    $before=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
    Copy-Item -LiteralPath $source -Destination $destination
    $copied=(Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash
    $after=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
    if($before -ne $copied -or $before -ne $after){throw ('CLIENT_DATA_CHANGED='+$file)}
    $files+=@([ordered]@{File=$file;SHA256=$copied.ToLowerInvariant();Bytes=$item.Length})
}
$pythonPath=Join-Path $PSScriptRoot 'Read-Client291-WorldDefinitions.py'
$python=[IO.File]::ReadAllBytes($pythonPath)
if(([BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash($python))).Replace('-','').ToLowerInvariant() -ne '1ab78664101a252c1f6d7857ffc55027b25a5f9306781344c89d1e0fce68ee18'){throw 'OWN_READER_DIFFERS'}
'LASU_DEFINICIJAS; SPELE_NAV_JAPALAIZ; SSH_IEVADI_TIKAI_TESTA_VM_PAROLI'
$savedOutputEncoding=$OutputEncoding
try {
    $OutputEncoding=[Text.UTF8Encoding]::new($false)
    $text=([Text.Encoding]::UTF8.GetString($python) | & ssh.exe -T -o ConnectTimeout=10 root@192.168.56.101 python3 - | Out-String)
    $sshExit=$LASTEXITCODE
} finally { $OutputEncoding=$savedOutputEncoding }
if($sshExit -ne 0){throw 'NATIVE_QUEST_READ_FAILED'}
$server=$text | ConvertFrom-Json
if($server.Schema -ne 1 -or $server.Changes -ne $false -or $server.QuestBytes -le 0 -or $server.QuestBytes -gt 8MB){throw 'NATIVE_REPORT_SHAPE'}
$native=[Convert]::FromBase64String($server.QuestBase64)
if($native.Length -ne $server.QuestBytes){throw 'NATIVE_QUEST_EXTENT'}
$nativePath=Join-Path $folder 'Native-Quest.scp'
[IO.File]::WriteAllBytes($nativePath,$native)
if((Get-FileHash -LiteralPath $nativePath -Algorithm SHA256).Hash -ne $server.QuestSHA256){throw 'NATIVE_QUEST_HASH'}
$report=[ordered]@{Schema=1;CollectedUTC=[DateTime]::UtcNow.ToString('o');MainSHA256='52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9';ClientFiles=$files;NativeQuestSHA256=$server.QuestSHA256;NativeQuestBytes=$native.Length;RunningWorldSHA256=$server.WorldSHA256;NativeQuestCountsRead=$server.QuestLoadedAttested;LoadedQuestStatus=$server.LoadedQuestStatus;LoadedQuestRows=$server.LoadedQuestRows;ClientLoadedDefinitionsAttested=$false;GameStarted=$false;Installation=$false;ServerChanges=$false;SQL=$false;CredentialsExported=$false}
$report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $folder 'DefinitionProfile.json') -Encoding UTF8
$zip=Join-Path $downloads ($name+'.zip')
$members=@(Get-ChildItem -LiteralPath $folder -File | Select-Object -ExpandProperty FullName)
Compress-Archive -LiteralPath $members -DestinationPath $zip
'ZIP='+$zip
'TIKAI_DEFINICIJU_KOPIJAS; SPELE_SERVERIS_UN_SQL_NAV_MAINITI'
