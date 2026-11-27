from app.engine import AnimationEngineUnavailable, UnconfiguredAnimationEngine
from app.schemas import GenerationMode, GenerationRequest, MotionFrame


async def test_unconfigured_engine_refuses_recording_generation(tmp_path) -> None:
    engine = UnconfiguredAnimationEngine()
    request = GenerationRequest(
        mode=GenerationMode.RECORDING,
        source_media_id="source-image-001",
        motion_media_id="motion-video-001",
        consent_record_id="consent-record-01",
    )
    try:
        await engine.generate_recording(
            request,
            tmp_path / "source.png",
            tmp_path / "motion.mp4",
            tmp_path / "output.mp4",
        )
    except AnimationEngineUnavailable as error:
        assert "not been trained or installed" in str(error)
    else:
        raise AssertionError("Unconfigured engine must not claim generation succeeded.")


async def test_unconfigured_engine_refuses_live_frame_generation(tmp_path) -> None:
    engine = UnconfiguredAnimationEngine()

    async def motion_stream():
        yield MotionFrame(sequence=0, timestamp_ms=0)

    try:
        async for _ in engine.generate_live_frames(
            tmp_path / "source.png",
            motion_stream(),
        ):
            pass
    except AnimationEngineUnavailable as error:
        assert "not available" in str(error)
    else:
        raise AssertionError("Unconfigured engine must not emit fake frames.")
