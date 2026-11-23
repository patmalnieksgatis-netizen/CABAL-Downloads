# Diamond v291 — first real Server01 atomic WorldSvr to ODBC fullchain

Date: 2026-11-23. Target: EP36_291_TEST / cabal_main.
Original WorldSvr SHA256 caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3.

**Status: source integrated and CI PASS; no VM SQL or WorldSvr changes.
In-game Diamond is NOT yet activated.**

## Code delivered

1. **DiamondWorldSessionAuthority.h** makes the existing v14
   WorldSessionAuthority exclusive lease available independently of
   synthetic ODBC Lab, without changing the previous bridge interface.
2. **Diamond0BDAAuthenticatedIngress.h/.cpp** acquires genuine
   host-provided exclusive WorldSvr session lease and validates
   USERCONTEXT+0xE8 UserData pointer, UserNum at UserData+0x890,
   CharacterIdx at UserData+0xA24, plus registry identity and generation.
   Holds lease through the GameData callback. Does not trust client IDs.
   0B10 Platinum passes through untouched.
3. **DiamondB0SelectedDebit30.h** builds an owned 30-byte-record
   GameData blob clone and exactly 100 ticket units debit after
   independent WorldSvr-slot / saved-physical-slot / serial mapping and
   independently verified B0 quantity codec. 999 to 899 and
   60+80 to 40 supported in SYNTHETIC fixtures. Full-stack deletion
   blocked without separate proof. No GameData write.
4. **00_server01_clone_atomic_rankup_v291.sql** contains a real
   SQL Server procedure prototype using actual owner-verified tables:
   dbo.cabal_Inventory_table(CharacterIdx PK, Data varbinary(max))
   dbo.cabal_WarExp_Table(CharacterIdx PK, WarExp, WarExpEarn, WarExpUsed)
   and NEW companion grade/receipt ledgers (not the client-native
   Grade2 format). SERIALIZABLE, XACT_ABORT, sp_getapplock per UserNum,
   Inventory and WarExp compare-and-swap, 30000 WarExp debit, Grade1 to
   Grade2 CAS and a uniquely constrained intent receipt in one COMMIT.
   Retries of the same committed intent do not double-debit.
   No account mapping is auto-created, no public EXECUTE granted.
   **Installation deliberately stops by default:** clone approval
   gate is absent, and first batch always rejects unless operator
   explicitly changes it for a separately VERIFIED restoreable clone.
5. **DiamondRealGameDataOdbc.h/.cpp** is real C++ ODBC call plumbing,
   staging exact-100 GameData material debit, checking trusted owner,
   clone proof, WarExp snapshots and a DB_NAME()=Server01 check, then
   calling the stored procedure with 12 bound parameters.
   It reads back the durable receipt with SHA2_256 of changed
   inventory. Any transport uncertainty after SQL mutation attempt
   returns InDoubtRecoveryRequired and is NEVER retried blindly.
6. **Diamond0BDARealServer01Bridge.h/.cpp** physically wires
   authenticated WorldSvr 0BDA ingress to the real ODBC callback
   and receipt check. The callback remains default-disabled until
   host runtime proof and clone approval exist.

## What tests actually prove

- Original v14 owner offset reader and 0BDA handler compile together.
- A synthetic valid owner lease remains held THROUGH the commit call.
- Stale session, alien UserNum / CharacterIdx and wrong registry pointer
  reject before writing.
- Real B0/999 materials may stage 999 to 899 only when independent
  quantity, item flags and slot mapping proofs are supplied.
- SQL procedure static tests verify the transactional CAS, receipt
  uniqueness, no shadow wallet and clone/no-grant gates.
- C++ ODBC callback compiles/links, rejects unverified inputs before
  opening an SQL connection.
- test_real_server01_dispatch_chain.cpp builds/links the whole path
  (v14 WorldSvr owner -> 0BDA -> real B0 inventory -> ODBC).
- GitHub Actions run 45248282385 at commit 2926f8916e41baaa65f516acb4a16f8d77cd0c10
  PASSED all native tests; companion SQL safety and Offline Policy PASSED.

## What remains before deployment

A. **No WorldSvr procedure registration:** 0x0BDA is absent in the
   original executable; prior experimental sidecar caused exit 78.
   Need known-good ABI for PROCEDUREMAP allocation and recovery.
B. **No actual v291 online WorldSvr owner implementation:** v14 offsets
   and mock owner are validated offline only; true session lock,
   48-byte item slot to persisted 30-byte slot/serial mapping,
   and true B0 quantity must be observed before enabling.
C. **No online GameData cmd46/47 save integration:** an out-of-band
   database write may be overwritten by later WorldSvr/DBAgent saves.
   A SQL receipt alone is NOT enough for a client success reply.
D. **WarExpUsed and WarExpEarn behavior unverified:** SQL prototype
   compares them and leaves them unchanged. Do not enable until
   the original v291 WExp accounting is understood.
E. **Native Diamond grade format and v291 client S2C reply ABI
   unverified:** the new SQL rank/receipt table is a standalone
   durable prototype, not proof that the UI will display Diamond.
F. **Clone approval and owner mapping provisioning are deliberately
   incomplete** and all enabling flags are FALSE by default.

**Nothing has been installed on the owner's EP36_291_TEST VM.**
Green CI proves source correctness, not live game behavior.
