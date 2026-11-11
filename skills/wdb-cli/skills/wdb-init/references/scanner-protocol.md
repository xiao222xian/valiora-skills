# Scanner and Managed Key Protocol

## Scanner invocation

```text
wechat-key-scanner DB_DIR OUTPUT_JSON
wechat-key-scanner --capture-passphrase DB_DIR OUTPUT_JSON [TIMEOUT_SECONDS]
wechat-key-scanner --probe-task-access PID
wechat-key-scanner --self-test
```

`DB_DIR` is an account `db_storage` directory or a private first-page snapshot
of the same relative layout. The scanner recursively collects encrypted
`.db` files, verifies SQLCipher page HMACs, and writes:

```json
{
  "message/message_0.db": {
    "enc_key": "<64 hex characters>"
  }
}
```

Important status strings include `WECHAT_NOT_RUNNING`,
`TASK_FOR_PID_DENIED`, `PASSPHRASE_REQUIRED`,
`PASSPHRASE_CAPTURE_TIMEOUT`, `PASSPHRASE_VERIFY_FAILED`, and
`SELF_TEST_OK`.

## Managed key file

`wdb-pro-managed-keys.json` is a list:

```json
[
  {
    "path": "/absolute/path/to/message_0.db",
    "key": "0123456789abcdef...",
    "cipherCompatibility": 4
  }
]
```

The directory must be mode `0700` and the file mode `0600`. The query module
normalizes `key` into a SQLCipher `PRAGMA key` value without writing it to
diagnostics.

## Architecture

Only the first 4096 bytes of each encrypted database are staged for key
verification. During login capture, WDB Pro creates a disposable debuggable
copy of WeChat, runs the scanner against the staged pages, then restores the
installed app. The original WeChat is never modified and SIP does not need to
be disabled.
