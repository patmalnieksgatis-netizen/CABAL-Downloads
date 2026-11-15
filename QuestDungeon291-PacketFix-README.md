# First v291 quest/dungeon packet correction

The old adapter counted every XML `mission` as a progress-vector element. That
was wrong for type2: the original v291 parser stores its dungeon condition in
the quest's scalar fields7C/80 and appends no vector entry. Consequently the old
profile added an unnecessary byte to46 quest records and rejected another8 mixed
scalar/progress records. The extra byte could shift all following World streams.

`audit_client291_quest_progress_semantics.py` executes the pinned original parser
and World-consumer fragments in Unicorn. Only strcmp/atoi are API stubs. Type2
stores4228/2 in the actual scalar fields and leaves all progress vectors empty.
The actual World consumer then consumes exactly0/1/2 supplied item-progress bytes,
preserves their values and leaves the following sentinel untouched. It never
reads a progress byte for the scalar dungeon condition.

The corrected profile compares actual loaded native group counts against the
real v291 progress-vector types. All1141 quests with identical goal definitions
match exactly; no synthetic quest progress is needed. The seven-byte record,
every real progress byte and the following source streams are copied unchanged.
Existing Guardian projection, costume pages and other World conversions remain.

The first update clones the currently active owned launcher profile. It replaces
only the World blob, its C# hash constant, and corresponding owned metadata. Any
unrelated existing runtime additions remain byte-identical. It retains the old
profile and backs up active.json before an atomic publication. The updater reads
the designated test VM's UUID, running World hash, Quest.scp hash and all1141
definition-group counts twice. Host /proc access with Docker NSpid mapping avoids
assuming that container root can read another process's memory.

There are no server/service/SQL writes, original game-data/DLL replacements, new
resource hooks, Start.bat changes or automatic game launch. The updater prints
`PALAIDEJS=` with the new Launcher.exe path and `IEPRIEKSEJAIS_PALAIDEJS=` with the
retained previous one. Launch the new executable manually for the gameplay test.

Verification:948 actual own-blob host checks pass, including all8 mixed records,
20 simultaneous scalar conditions, exact65535 frame boundary and later costume
pages. The historical baseline still passes873 checks. Eighteen Python tests
cover bulk/data graph/editor/updater behavior. The updater's real PowerShell
transaction passes success/repeat, server refusal, compiler refusal, tampered
member and publication-failure rollback cases with explicit boundary stubs.
The updated C# runtime actually compiles; PowerShell parses. These checks do not
establish Windows SDK integration or gameplay success.

This is a limited first correction. The31 changed objective sets,14 native-only
definitions, missing dungeon4637, target annotations and complete dungeon logic
remain open. It does not grant Legend Wings, Diamond Insignia or character state.
The generic decoded-resource editor is an offline component, not part of this
release. Full quest/dungeon alignment has not been claimed or installed.
