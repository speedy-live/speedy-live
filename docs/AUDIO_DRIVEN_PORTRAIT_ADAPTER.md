# Audio-Driven Portrait Adapter Contract

**Status:** Backend input/interface foundation only. No audio-driven model adapter is installed.

## Inputs

A portrait session uses:
- A consented portrait image reference (`portrait_media_id`).
- A speech audio reference (`speech_audio_media_id`) for the speaking participant.
- An optional listening audio reference (`listening_audio_media_id`) for the listening participant.
- A consent record reference.

The current media IDs are references only. This change does not implement file upload, object storage, transcoding, recording, or media retrieval.

For streaming adapters, `AudioChunk` represents bounded PCM input:
- Supported sample rates: 16, 24, 44.1, and 48 kHz.
- Mono or stereo.
- Signed 16-bit little-endian PCM or 32-bit float little-endian PCM.
- Base64 payload with a maximum decoded size of 256 KiB per chunk.
- Monotonically increasing sequence and timestamp values must be validated per track.

Speech and listening audio are distinct tracks. Never mix them implicitly. The model adapter must document which track drives lip synchronisation and how listening audio is used for idle/listening expressions. If the selected model does not support a listening track, the adapter must explicitly declare that limitation rather than fabricate an input.

## Engine interface

A concrete local adapter may implement `AnimationEngine.generate_audio_driven_frames(source_image, speech_audio, listening_audio)`. The default method deliberately raises `AnimationEngineUnavailable`; an adapter that only implements motion-landmark animation cannot claim audio-driven support.

The adapter manifest must explicitly set `supports_audio_driven_portrait=true`. The registry requires:
- Portrait mode support.
- Live streaming support for live sessions.
- Explicit audio-driven portrait capability.
- Existing artifact hash, rights, consent, runtime-health and customer-release gates.

The audio-driven capability is separate from ordinary portrait capability. Full-body animation is not implied by this interface.

## Synchronisation and runtime responsibilities

An actual adapter must specify and test:
- Audio codec, sample rate, channel layout and resampling policy.
- Chunk duration and maximum buffering.
- Speech/listening track clock alignment and timestamp origin.
- Handling of missing, late, duplicated and out-of-order chunks.
- Audio/video presentation timestamps and output frame rate.
- Backpressure, bounded queues, cancellation and session cleanup.
- Maximum session duration, memory and GPU limits.
- Lip-sync offset distribution and end-to-end p50/p95 latency.

Do not drop or reorder audio silently. Do not let an unbounded queue accumulate when inference is slower than incoming audio. The adapter must expose real runtime self-test behavior and must not report healthy merely because imports or model files are present.

## Safety and privacy

Media IDs must resolve only to private, access-controlled storage after authentication and consent checks. The audio contract does not authorize voice cloning, reuse of customer audio for training, or use of another person's identity without permission. Customer media is not training data by default. Keep raw media and checkpoints out of Git.

## Current implementation boundary

Implemented:
- Validated request references and consent ID.
- Bounded base64 PCM chunk schema.
- Sample-rate, channel, encoding, byte-alignment and chunk-size validation.
- Strict sequence/timestamp validation helper.
- Optional audio-driven method on the local engine interface.
- Explicit registry capability flag and fail-closed checks.

Not implemented:
- Audio upload/storage and authenticated media resolution.
- WebSocket/WebRTC audio transport.
- Audio decoding, resampling, VAD or diarisation.
- Model-specific speech/listening conditioning.
- Actual generated video frames, audio/video muxing or recording output.
- Live-call orchestration, network jitter handling or end-to-end latency measurements.

A passing contract test is not evidence that an animation model can generate video.
