# protocols_.py Bug Fix

The official `protocols_.py` from the volcengine docs has a critical bug in
`_get_writers()` and `_get_readers()` methods of the `Message` class.

## The Problem

The `WithEvent` flag (0b0100 = 4) is combined with sequence flags like
`LastNoSeq` (0b0010 = 2) by the server when sending audio messages,
producing flag value 0b0110 = 6.

But the code uses equality checks:
- `self.flag == MsgTypeFlagBits.WithEvent` (checks for exactly 4, never matches 6)
- `self.flag in [PositiveSeq, NegativeSeq]` (checks for exactly 1 or 3)

This causes audio messages to be parsed without their event/sequence fields,
silently losing data.

## Symptoms

- `TaskRequest` sent successfully but `AudioOnlyServer` messages are either
  not received or contain garbled data
- `TTSSentenceStart` received but audio payload is empty or corrupted
- `receive_message()` returns messages with `event=None_` when audio is expected

## The Fix

In `_get_writers()` and `_get_readers()`, change:

```python
# Line ~272 and ~310: Use bitwise AND for WithEvent
if self.flag & MsgTypeFlagBits.WithEvent:  # was: self.flag == ...

# Line ~282 and ~303: Mask lower 2 bits for sequence flags
if (self.flag & 0b11) in [MsgTypeFlagBits.PositiveSeq, MsgTypeFlagBits.NegativeSeq]:
    # was: self.flag in [...]
```

## Verification

After the fix, `receive_message()` correctly parses `AudioOnlyServer` messages
with combined flags, and audio payloads are extracted properly.
