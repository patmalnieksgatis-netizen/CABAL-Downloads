$ErrorActionPreference='Stop'
$root='F:\CABAL_291_TEST'
function Need($ok,[string]$why){if(!$ok){throw $why}}
function Sha([byte[]]$b){$h=[Security.Cryptography.SHA256]::Create();try{return ([BitConverter]::ToString($h.ComputeHash($b))).Replace('-','').ToLowerInvariant()}finally{$h.Dispose()}}
function Md5([byte[]]$b){$h=[Security.Cryptography.MD5]::Create();try{return ([BitConverter]::ToString($h.ComputeHash($b))).Replace('-','').ToLowerInvariant()}finally{$h.Dispose()}}
function Bytes([string]$p){return [IO.File]::ReadAllBytes($p)}
Need (Test-Path -LiteralPath "$root\Bin\x64\CabalMain.exe") 'TEST_CLIENT_NOT_FOUND'
Need ((Get-FileHash -LiteralPath "$root\Bin\x64\CabalMain.exe" -Algorithm SHA256).Hash -eq '52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9') 'CLIENT_BUILD_DIFFERS'
$running=@(Get-CimInstance Win32_Process -Filter "Name='CabalMain.exe'" | Where-Object {$_.ExecutablePath -and $_.ExecutablePath.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)})
Need ($running.Count -eq 0) 'AIZVER_SPELI_UN_PALAID_ATKARTOTI'
Add-Type -AssemblyName System.IO.Compression.FileSystem
$scp=$null
foreach($zip in @(Get-ChildItem -LiteralPath (Join-Path $env:USERPROFILE 'Downloads') -Filter 'BumbleBee-ItemOptions-*.zip' -File -Recurse -ErrorAction SilentlyContinue)){
 $z=[IO.Compression.ZipFile]::OpenRead($zip.FullName)
 try{$e=$z.GetEntry('report.json');if(!$e -or $e.Length -gt 8388608){continue};$reader=[IO.StreamReader]::new($e.Open());try{$report=$reader.ReadToEnd()|ConvertFrom-Json}finally{$reader.Dispose()};foreach($row in $report.Definitions){if($row.Name -ieq 'ForceWing.scp'){$b=[Convert]::FromBase64String($row.Base64);if((Sha $b) -eq 'a61ac14f2218a44fae34053f93aa4fcd458fe22ae5f97f312443c7df0c47f052'){$scp=$b;break}}}}finally{$z.Dispose()}
 if($null -ne $scp){break}
}
Need ($null -ne $scp) 'NAV_IEPRIEKSEJA_BUMBLEBEE_ITEMOPTIONS_ZIP_DOWNLOADS_MAPE; NEKAS_NAV_MAINITS'
$stage=Join-Path $env:TEMP ('Client291-DataRestore-'+[guid]::NewGuid().ToString('N'));[void][IO.Directory]::CreateDirectory($stage)
$source=$null
foreach($candidate in @('F:\CABAL','F:\ CABAL')){
 if((Test-Path -LiteralPath "$candidate\Bin\x64\CabalMain.exe") -and (Test-Path -LiteralPath "$candidate\xdata.enc") -and (Test-Path -LiteralPath "$candidate\Data\ForceWing.enc")){
  if((Get-FileHash -LiteralPath "$candidate\Bin\x64\CabalMain.exe" -Algorithm SHA256).Hash -eq '52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9' -and (Md5 (Bytes "$candidate\xdata.enc")) -eq '5ed28699bb31d6e43f52e246520fe003' -and (Sha (Bytes "$candidate\Data\ForceWing.enc")) -ne 'b9689958b7fe22eddb1a77fba4fde9cac71229b52d9c6b6b4a83a4945a644552'){$source=$candidate;break}
 }
}
if($source){
 Copy-Item -LiteralPath "$source\xdata.enc" -Destination "$stage\xdata.enc"
 Copy-Item -LiteralPath "$source\Data\ForceWing.enc" -Destination "$stage\ForceWing.enc"
 Write-Output ('ORIGINAL_CLIENT_SOURCE='+$source)
}else{
 $cdn='https://cabal.b-cdn.net/C:/PlayCabal/'
 Write-Output 'GAIDU_TA_PASA_V291_ORIGINALOS_FAILUS; VERSIJA_TIKS_PARBAUDITA'
 Invoke-WebRequest -UseBasicParsing ($cdn+'GameFileList.json.gz') -OutFile "$stage\manifest.gz"
 $manifestStream=[IO.File]::OpenRead("$stage\manifest.gz");$gzip=[IO.Compression.GZipStream]::new($manifestStream,[IO.Compression.CompressionMode]::Decompress);$reader=[IO.StreamReader]::new($gzip)
 try{$manifest=$reader.ReadToEnd()|ConvertFrom-Json}finally{$reader.Dispose();$gzip.Dispose();$manifestStream.Dispose()}
 $main=@($manifest|Where-Object {($_.u -replace '^/','') -ieq 'Bin/x64/CabalMain.exe'})
 Need ($main.Count -eq 1 -and $main[0].h -eq '02e46048c0d02cd743345c4b6f5bcc3f') 'DOWNLOAD_SOURCE_IS_NOT_OUR_V291_BUILD; NOTHING_CHANGED'
 foreach($relative in @('xdata.enc','Data/ForceWing.enc')){
  $row=@($manifest|Where-Object {($_.u -replace '^/','') -ieq $relative});Need ($row.Count -eq 1) ('ORIGINAL_MANIFEST_ENTRY_MISSING_'+$relative)
  $file=Join-Path $stage ([IO.Path]::GetFileName($relative));Invoke-WebRequest -UseBasicParsing ($cdn+$relative) -OutFile $file
  Need ((Get-Item -LiteralPath $file).Length -eq $row[0].s -and (Md5 (Bytes $file)) -eq $row[0].h) ('ORIGINAL_DOWNLOAD_HASH_DIFFERS_'+$relative)
 }
}
Need ((Md5 (Bytes "$stage\xdata.enc")) -eq '5ed28699bb31d6e43f52e246520fe003') 'ORIGINAL_XDATA_PROFILE_DIFFERS; NOTHING_CHANGED'
Need ((Sha (Bytes "$stage\ForceWing.enc")) -ne 'b9689958b7fe22eddb1a77fba4fde9cac71229b52d9c6b6b4a83a4945a644552') 'DOWNLOADED_FORCEWING_IS_THE_REPLACEMENT; NOTHING_CHANGED'
$server=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('IiIiUmVzdG9yZSBvbmx5IHRoZSBleGFjdCBwcmUtY2hhbmdlIEZvcmNlV2luZy5zY3Agb24gdGhlIGlzb2xhdGVkIHRlc3QgVk0uIiIiCmltcG9ydCBiYXNlNjQsaGFzaGxpYixvcyxzdWJwcm9jZXNzLHN5cwpmcm9tIHBhdGhsaWIgaW1wb3J0IFBhdGgKClBBWUxPQUQ9J19fUkVTVE9SRV9TQ1BfQkFTRTY0X18nCklOTkVSPScnJ2ltcG9ydCBiYXNlNjQsaGFzaGxpYixvcyxwYXRobGliLHN1YnByb2Nlc3Msc3lzLHRlbXBmaWxlLHRpbWUKUD1wYXRobGliLlBhdGgKZ29vZD0iYTYxYWMxNGYyMjE4YTQ0ZmFlMzQwNTNmOTNhYTRmY2Q0NThmZTIyYWU1Zjk3ZjMxMjQ0M2M3ZGYwYzQ3ZjA1MiIKY2hhbmdlZD0iZmM0YzMwMzRhOTIzNTAzYjM5ZmVlYTZjNzM2NzZmM2Q0ZDg1ODc5MGUyNWU3NjAwNzc3ZDI4NjY0NmRhMDU2YSIKd29ybGQ9ImNhZWM3NzcyYWNkMjJmZDg5MThjZmFjMzg2ODQ1YzY0NDQ1MTc4MWU0OGM1MTk3NWVhZWZlZDMzNGM2NzA1YzMiCmRlZiBuZWVkKG9rLG1zZyk6CiBpZiBub3Qgb2s6cmFpc2UgUnVudGltZUVycm9yKG1zZykKZGVmIHNoYShiKTpyZXR1cm4gaGFzaGxpYi5zaGEyNTYoYikuaGV4ZGlnZXN0KCkKZGVmIHBpZChuKToKIHI9c3VicHJvY2Vzcy5ydW4oWyJzdXBlcnZpc29yY3RsIiwicGlkIixuXSxjYXB0dXJlX291dHB1dD1UcnVlLHRleHQ9VHJ1ZSx0aW1lb3V0PTE1KQogbmVlZChyLnN0ZG91dC5zdHJpcCgpLmlzZGlnaXQoKSwiU0VSVklDRV9QSURfVU5BVkFJTEFCTEUiKTtyZXR1cm4gaW50KHIuc3Rkb3V0LnN0cmlwKCkpCmRlZiBjb250cm9sKGFjdGlvbik6CiByPXN1YnByb2Nlc3MucnVuKFsic3VwZXJ2aXNvcmN0bCIsYWN0aW9uLCJXb3JsZFN2cl8wMV8wMSJdLGNhcHR1cmVfb3V0cHV0PVRydWUsdGltZW91dD0zNSkKIG5lZWQoci5yZXR1cm5jb2RlPT0wIG9yIChhY3Rpb249PSJzdG9wIiBhbmQgbm90IHBpZCgiV29ybGRTdnJfMDFfMDEiKSksIldPUkxEXyIrYWN0aW9uLnVwcGVyKCkrIl9GQUlMRUQiKQp0YXJnZXQ9UCgiL2V0Yy9jYWJhbC9EYXRhL0ZvcmNlV2luZy5zY3AiKTtuZWVkKHRhcmdldC5pc19maWxlKCkgYW5kIG5vdCB0YXJnZXQuaXNfc3ltbGluaygpLCJTRVJWRVJfRk9SQ0VXSU5HX1BBVEhfRElGRkVSUyIpCmJvZHk9YmFzZTY0LmI2NGRlY29kZSgiX19QQVlMT0FEX18iLHZhbGlkYXRlPVRydWUpO25lZWQoc2hhKGJvZHkpPT1nb29kLCJSRVNUT1JFX1NPVVJDRV9ESUZGRVJTIikKYmVmb3JlPXRhcmdldC5yZWFkX2J5dGVzKCk7bmVlZChzaGEoYmVmb3JlKSBpbiAoZ29vZCxjaGFuZ2VkKSwiVU5SRUNPR05JWkVEX1NFUlZFUl9GT1JDRVdJTkc7IE5PVEhJTkdfQ0hBTkdFRCIpCnA9cGlkKCJXb3JsZFN2cl8wMV8wMSIpO2xvZ2luPXBpZCgiTG9naW5TdnJfMDEiKQpleGU9UCgiL3Byb2MiKS9zdHIocCkvImV4ZSIgaWYgcCBlbHNlIFAoIi9ldGMvY2FiYWwvbWlncmF0aW9uX3Rvb2xzL2VwMzYtY29zdHVtZS10cmlhbC12MS9uYXRpdmUvV29ybGRTdnJfMDFfMDEiKQpuZWVkKHNoYShleGUucmVhZF9ieXRlcygpKT09d29ybGQsIldPUkxEX1BST0ZJTEVfRElGRkVSUyIpCmlmIHN5cy5hcmd2WzFdPT0iLS1jaGVjayI6cHJpbnQoIkZPUkNFV0lOR19TRVJWRVJfUFJFRkxJR0hUX09LIik7c3lzLmV4aXQoMCkKbmVlZChzeXMuYXJndlsxXT09Ii0tYXBwbHkiLCJBQ1RJT05fUkVRVUlSRUQiKQppZiBzaGEoYmVmb3JlKT09Z29vZDpwcmludCgiRk9SQ0VXSU5HX1NFUlZFUl9BTFJFQURZX09SSUdJTkFMOyBOT19SRVNUQVJUIik7c3lzLmV4aXQoMCkKYmFja3VwPVAoIi9ldGMvY2FiYWwvbWlncmF0aW9uX3Rvb2xzL2ZvcmNld2luZy1yZXN0b3JlLTIwMjYxMTE0Iik7YmFja3VwLm1rZGlyKG1vZGU9MG83MDAsZXhpc3Rfb2s9VHJ1ZSkKbmVlZChub3QgYmFja3VwLmlzX3N5bWxpbmsoKSBhbmQgbm90IGJhY2t1cC5zdGF0KCkuc3RfbW9kZSYwbzA3NywiVU5TQUZFX0JBQ0tVUF9ESVJFQ1RPUlkiKQpvbGQ9YmFja3VwLyJGb3JjZVdpbmcuYmVmb3JlLnNjcCIKaWYgb2xkLmV4aXN0cygpOm5lZWQoc2hhKG9sZC5yZWFkX2J5dGVzKCkpPT1jaGFuZ2VkLCJCQUNLVVBfRElGRkVSUyIpCmVsc2U6b2xkLndyaXRlX2J5dGVzKGJlZm9yZSk7b2xkLmNobW9kKDBvNjAwKQptb2RlPXRhcmdldC5zdGF0KCkuc3RfbW9kZSYwbzc3NwppZiBwOmNvbnRyb2woInN0b3AiKQpmZCxuYW1lPXRlbXBmaWxlLm1rc3RlbXAocHJlZml4PSIuZm9yY2V3aW5nLXJlc3RvcmUtIixkaXI9dGFyZ2V0LnBhcmVudCkKdHJ5Ogogd2l0aCBvcy5mZG9wZW4oZmQsIndiIikgYXMgZjpmLndyaXRlKGJvZHkpO2YuZmx1c2goKTtvcy5mc3luYyhmLmZpbGVubygpKQogb3MuY2htb2QobmFtZSxtb2RlKTtvcy5yZXBsYWNlKG5hbWUsdGFyZ2V0KQpmaW5hbGx5OgogaWYgb3MucGF0aC5leGlzdHMobmFtZSk6b3MudW5saW5rKG5hbWUpCm5lZWQoc2hhKHRhcmdldC5yZWFkX2J5dGVzKCkpPT1nb29kLCJTRVJWRVJfUkVTVE9SRV9SRUFEQkFDS19GQUlMRUQiKQpjb250cm9sKCJzdGFydCIpCmRlYWRsaW5lPXRpbWUubW9ub3RvbmljKCkrNDU7c3RhYmxlPTA7c2luY2U9MAp3aGlsZSB0aW1lLm1vbm90b25pYygpPGRlYWRsaW5lOgogY3VycmVudD1waWQoIldvcmxkU3ZyXzAxXzAxIik7bmVlZChwaWQoIkxvZ2luU3ZyXzAxIik9PWxvZ2luLCJMT0dJTl9QSURfQ0hBTkdFRCIpCiBpZiBjdXJyZW50IGFuZCBjdXJyZW50PT1zdGFibGUgYW5kIHRpbWUubW9ub3RvbmljKCktc2luY2U+PTg6CiAgbmVlZChzaGEoKFAoIi9wcm9jIikvc3RyKGN1cnJlbnQpLyJleGUiKS5yZWFkX2J5dGVzKCkpPT13b3JsZCwiV09STERfQ0hBTkdFRCIpCiAgcHJpbnQoIkZPUkNFV0lOR19TRVJWRVJfT1JJR0lOQUxfUkVTVE9SRUQ7IFdPUkxEX1JVTk5JTkc7IE5PX1NRTF9DSEFOR0VTIik7c3lzLmV4aXQoMCkKIGlmIGN1cnJlbnQhPXN0YWJsZTpzdGFibGU9Y3VycmVudDtzaW5jZT10aW1lLm1vbm90b25pYygpCiB0aW1lLnNsZWVwKDEpCnJhaXNlIFJ1bnRpbWVFcnJvcigiRk9SQ0VXSU5HX0ZJTEVfUkVTVE9SRUQ7IFdPUkxEX1NUQVJUX05PVF9DT05GSVJNRUQiKQonJycKCmRlZiBtYWluKCk6CiAgICBpZiBvcy5nZXRldWlkKCkhPTAgb3IgUGF0aCgnL3N5cy9jbGFzcy9kbWkvaWQvcHJvZHVjdF91dWlkJykucmVhZF90ZXh0KCkuc3RyaXAoKS5sb3dlcigpIT0nNzYzMmZiNzgtMzdhMC1mNjQ1LTk3YzAtZGMzMjJjNTBiMDAyJzoKICAgICAgICByYWlzZSBTeXN0ZW1FeGl0KCdXUk9OR19URVNUX1ZNX09SX1JPT1RfUkVRVUlSRUQ7IE5PVEhJTkdfQ0hBTkdFRCcpCiAgICBpZiBzeXMuYXJndlsxOl0gbm90IGluIChbJy0tY2hlY2snXSxbJy0tYXBwbHknXSk6cmFpc2UgU3lzdGVtRXhpdCgnQUNUSU9OX1JFUVVJUkVEJykKICAgIGJvZHk9YmFzZTY0LmI2NGRlY29kZShQQVlMT0FELHZhbGlkYXRlPVRydWUpCiAgICBpZiBoYXNobGliLnNoYTI1Nihib2R5KS5oZXhkaWdlc3QoKSE9J2E2MWFjMTRmMjIxOGE0NGZhZTM0MDUzZjkzYWE0ZmNkNDU4ZmUyMmFlNWY5N2YzMTI0NDNjN2RmMGM0N2YwNTInOnJhaXNlIFN5c3RlbUV4aXQoJ1NPVVJDRV9TQ1BfRElGRkVSUycpCiAgICByZXN1bHQ9c3VicHJvY2Vzcy5ydW4oWydkb2NrZXInLCdleGVjJywnLWknLCdjYWJhbF9tYWluJywncHl0aG9uMycsJy0nLHN5cy5hcmd2WzFdXSxpbnB1dD1JTk5FUi5yZXBsYWNlKCdfX1BBWUxPQURfXycsUEFZTE9BRCkuZW5jb2RlKCkpCiAgICByYWlzZSBTeXN0ZW1FeGl0KHJlc3VsdC5yZXR1cm5jb2RlKQoKaWYgX19uYW1lX189PSdfX21haW5fXyc6bWFpbigpCg==')).Replace('__RESTORE_SCP_BASE64__',[Convert]::ToBase64String($scp))
$server | ssh root@192.168.56.101 python3 - --check
Need ($LASTEXITCODE -eq 0) 'SERVER_PREFLIGHT_FAILED; CLIENT_NOT_CHANGED'
$backup=Join-Path ([Environment]::GetFolderPath('MyDocuments')) ('CABAL291-Data-RestoreBackups\'+[guid]::NewGuid().ToString('N'));[void][IO.Directory]::CreateDirectory($backup)
$plan=@(@{Target="$root\xdata.enc";Source="$stage\xdata.enc";Backup="$backup\xdata.before.enc"},@{Target="$root\Data\ForceWing.enc";Source="$stage\ForceWing.enc";Backup="$backup\ForceWing.before.enc"})
foreach($row in $plan){Need (Test-Path -LiteralPath $row.Target -PathType Leaf) ('TARGET_MISSING_'+$row.Target);Copy-Item -LiteralPath $row.Target -Destination $row.Backup}
try{foreach($row in $plan){Copy-Item -LiteralPath $row.Source -Destination $row.Target -Force;Need ((Sha (Bytes $row.Target)) -eq (Sha (Bytes $row.Source))) 'CLIENT_RESTORE_READBACK_FAILED'}}catch{foreach($row in $plan){Copy-Item -LiteralPath $row.Backup -Destination $row.Target -Force};throw}
Write-Output 'CLIENT_XDATA_AND_FORCEWING_ORIGINALS_RESTORED'
Write-Output ('BACKUP='+$backup)
$server | ssh root@192.168.56.101 python3 - --apply
Need ($LASTEXITCODE -eq 0) 'CLIENT_FILES_RESTORED; SERVER_RESTORE_NOT_CONFIRMED; ATSUTI_IZVADI'
Write-Output 'CLIENT291_THREE_FILES_RESTORED; PALAID_AR_ESOSO_PALAIDEJU'
