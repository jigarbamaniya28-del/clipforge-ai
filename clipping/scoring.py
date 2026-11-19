
def calculate_clip_score(
    hook_quality,
    entertainment,
    context,
    audio_quality,
    visual_quality
):
    score = (
        hook_quality * 0.25 +
        entertainment * 0.25 +
        context * 0.20 +
        audio_quality * 0.15 +
        visual_quality * 0.15
    )

    return round(score, 1)


def rank_clips(clips):
    return sorted(
        clips,
        key=lambda clip: clip["score"],
        reverse=True
    )
