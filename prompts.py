"""Prompt builder for the jewelry mix-and-match pipeline.

Lives in its own module so it can be imported by both the Streamlit app
and offline test harnesses without dragging in UI code.
"""


def build_combine_prompt(image_specs, additional_specs):
    """Master prompt tuned for fal-ai/bytedance/seedream/v4/edit.

    Seedream v4 responds best to tight imperative prompts with crisp
    per-image extraction lines and short rule blocks. Avoid long meta
    framing — Seedream handles structural fidelity natively when told
    plainly.
    """
    active_specs = [s for s in image_specs if s["file"] and s["description"]]

    ref_lines = []
    component_summary = []
    extracted_descs = [s["description"].strip().rstrip(".") for s in active_specs]
    for i, spec in enumerate(active_specs):
        n = i + 1
        desc = extracted_descs[i]
        other_descs = [d for j, d in enumerate(extracted_descs) if j != i]
        ignore_clause = (
            f"DO NOT use, reference, or borrow from any other part of Image {n} "
            f"— in particular, IGNORE Image {n}'s "
            + (
                ", ".join(other_descs)
                if other_descs
                else "other components"
            )
            + ", structural features (cutouts, gaps, openings, bezel housings, "
            "tension brackets), surface decoration, and stones. Those parts "
            "must NOT appear in the output."
        )
        ref_lines.append(
            f"- From Image {n}: take ONLY the {desc}. Reproduce it 1:1 — "
            f"exact metal color (rose-gold stays rose-gold, yellow-gold stays "
            f"yellow-gold, white-gold stays white-gold, platinum stays "
            f"platinum), shape, prongs, stones, surface finish, profile, "
            f"width, taper, and proportions. {ignore_clause}"
        )
        component_summary.append(f"the {desc} (from Image {n})")

    refs_block = "\n".join(ref_lines)
    components_text = " + ".join(component_summary)

    component_checklist = "\n".join(
        f"- Is the {spec['description'].strip().rstrip('.')} from Image {i+1} "
        f"visibly present in the output? It MUST be."
        for i, spec in enumerate(active_specs)
    )

    sections = [
        "Combine the reference images into ONE single new piece of jewelry. "
        "This is a precise part-swap — copy each extracted component exactly. "
        "Only the joint where components meet may be invented.",

        f"EXTRACT FROM EACH IMAGE\n{refs_block}",

        "CONSTRUCTION\n"
        f"Assemble: {components_text}. Connect them with a clean, "
        "structurally sound joint. Two-tone (or three-tone) metal is correct "
        "and intended — do not unify, average, or harmonize metal colors "
        "across components. If one component is rose-gold and the other is "
        "white-gold, the output shows rose-gold meeting white-gold at a "
        "crisp boundary. If three different metal colors appear across the "
        "components, all three appear in the output.",

        "EXCLUSION RULES (CRITICAL)\n"
        "- The output's shank comes ONLY from the image whose shank was "
        "extracted. Do NOT carry the shank — its pavé, stones, profile, or "
        "decoration — from any other reference image, even if it looks more "
        "typical or more 'jewelry-like'.\n"
        "- The output's head comes ONLY from the image whose head was "
        "extracted. Do NOT borrow prongs, halos, or settings from any other "
        "reference.\n"
        "- Specific failure to avoid: extracting a head from Image 1 and a "
        "shank from Image 2, then producing an output where the shank is a "
        "blend of BOTH shanks (e.g., plain band with pavé added from Image 1, "
        "or Image 2's plain band with Image 1's pavé grafted on). The output "
        "shank must be a faithful reproduction of Image 2's shank ALONE.\n"
        "- Do NOT borrow structural features (cutouts, gaps, openings, "
        "bezel housings, tension brackets, frame windows) from a component "
        "you are NOT extracting. If Image 2's bezel structure is not part "
        "of the extracted shank, it must NOT appear in the output.",

        "ANTI-COPY RULE (CRITICAL)\n"
        "- The output MUST NOT be a copy or near-copy of any single "
        "reference image. It is a NEW piece that visibly fuses parts from "
        "every reference.\n"
        "- The output MUST visibly contain the specified component from "
        "EVERY reference image listed above. Missing any one of them is a "
        "failure.\n"
        "- If your output looks like Image 1 with no Image 2 elements (or "
        "vice versa), discard it and try again — that is the most common "
        "failure mode for this task.\n"
        "- Specifically: a viewer comparing the output side-by-side with "
        "the references must immediately see which part came from which "
        "reference.",

        "SILHOUETTE PRESERVATION (CRITICAL)\n"
        "- Reproduce the exact 2D outline and silhouette of each extracted "
        "component. If the head is shaped like a flower with petals, the "
        "output head is shaped like a flower with petals. If the head is a "
        "6-prong solitaire, the output head is a 6-prong solitaire.\n"
        "- Decorative elements that define the shape — petals, halos, "
        "leaves, scrollwork, filigree, openwork, basket cages — MUST appear "
        "in the output exactly as in the source.\n"
        "- Do NOT simplify an ornate component into a plain one (e.g., "
        "turning a flower halo into a bare 4-prong setting).\n"
        "- Do NOT embellish a plain component into an ornate one.\n"
        "- Color alone is not enough — match the SHAPE.",

        "SURFACE FINISH PRESERVATION\n"
        "- DEFAULT to high-polished, mirror-finish metal unless the source "
        "clearly shows a matte / brushed / satin / hammered / sandblasted "
        "texture. When in doubt, render polished — never default to matte.\n"
        "- If the source surface is high-polished and smooth, the output "
        "surface is high-polished and smooth.\n"
        "- Do NOT add brushed, hammered, knurled, satin, matte, sandblasted, "
        "wood-grain, or any textured finish that is not in the source.\n"
        "- Do NOT add milgrain edges, engraving lines, or hatching that is "
        "not in the source.",

        "MANUFACTURABILITY (CRITICAL)\n"
        "- The output must be a PHYSICALLY REALIZABLE piece of jewelry that "
        "could be cast, set, and worn in real life.\n"
        "- The INTERIOR of the shank (the surface that touches the finger) "
        "MUST be smooth and ROUND/CIRCULAR — never hexagonal, octagonal, "
        "polygonal, faceted, or angular. Even when the OUTSIDE of the "
        "shank has flat or geometric faces (architectural shanks, square "
        "profiles, etc.), the INSIDE remains a smooth circle so the ring "
        "fits a finger.\n"
        "- Every prong, claw, gallery, halo, and decorative element must "
        "be structurally connected to the metal — no floating elements, "
        "no impossible cantilevers, no detached components.\n"
        "- Every stone must sit in a plausible setting (prong, bezel, "
        "channel, pavé, flush) with visible metal supporting it from below "
        "and around. No stones floating in air.\n"
        "- Realistic proportions and weight balance — the piece must look "
        "like jewelry a real craftsman could actually fabricate.",

        "SYMMETRY\n"
        "- Decorative elements (pavé stones, channel-set stones, side "
        "diamonds, milgrain, halos, prongs, scrollwork) MUST appear "
        "symmetrically on both shoulders and both sides of the piece. If "
        "the source shank has pavé on both shoulders, the output shank has "
        "pavé on both shoulders — never on one side only.\n"
        "- The left and right halves of the ring must mirror each other "
        "unless the source is intentionally asymmetric.\n"
        "- The head's prongs must be evenly spaced and equal in size.",

        "PRESERVATION RULES (STRICT)\n"
        "- Do NOT add stones, diamonds, pavé, channel-set stones, halos, "
        "milgrain, engraving, filigree, or any decoration that is not "
        "visible on that component in its source image.\n"
        "- Do NOT remove stones, prongs, or details that ARE visible in "
        "the source component.\n"
        "- If a component is plain and smooth in the source, keep it plain "
        "and smooth. If it is set with stones, keep exactly those stones in "
        "the same arrangement.\n"
        "- Do NOT change band thickness, shoulder profile, prong count, "
        "prong shape, or stone size.\n"
        "- Do NOT redesign, stylize, or reinterpret — copy.",

        "COVERAGE / EXTENT (CRITICAL)\n"
        "- Preserve the EXTENT and COVERAGE area of every decorative "
        "feature, not just its presence. If the source shank has pavé "
        "running the FULL LENGTH of the band (from shoulder to shoulder), "
        "the output shank has pavé running the FULL LENGTH. Do NOT shrink "
        "full-length pavé into shoulder-only pavé.\n"
        "- If a halo wraps fully around the center stone in the source, it "
        "wraps fully in the output. Do NOT show a partial halo.\n"
        "- If milgrain, engraving, or filigree spans an entire edge in the "
        "source, it spans the entire edge in the output. Do NOT shorten "
        "or interrupt continuous decoration.\n"
        "- Match the START point and END point of every decorative band, "
        "not just the style.",
    ]

    if additional_specs.get("metal"):
        sections.append(
            f"METAL OVERRIDE\nRender the entire piece in {additional_specs['metal']}, "
            "replacing the original metal colors of all references. This "
            "overrides the color preservation rules above."
        )

    if additional_specs.get("stones"):
        sections.append(f"STONES\n{additional_specs['stones']}")

    if additional_specs.get("dimensions"):
        sections.append(f"PROPORTIONS\n{additional_specs['dimensions']}")

    if additional_specs.get("notes"):
        sections.append(f"NOTES\n{additional_specs['notes']}")

    sections.append(
        "OUTPUT\n"
        "One ring on a PURE WHITE seamless background — RGB(255,255,255), "
        "not gray, not cream, not off-white, not ivory, not warm-tinted, "
        "not tinted — with only a subtle soft shadow directly under the "
        "piece. IGNORE the background color of any input reference image; "
        "if a reference has a cream or tinted background, the output "
        "background is STILL pure white RGB(255,255,255). Professional "
        "jewelry product photography, neutral-balanced studio lighting "
        "(no warm cast), ultra-sharp macro detail, centered three-quarter "
        "angle, the piece occupying roughly 70% of the frame. No hands, "
        "no models, no props, no text, no watermarks, no logos, no "
        "collage of references."
    )

    sections.append(
        f"VERIFY BEFORE FINALIZING\n{component_checklist}\n"
        f"- Does each extracted component keep its original metal color? It MUST.\n"
        f"- Does each extracted component keep its original SHAPE/silhouette "
        f"(petals, halos, prong count, band profile)? It MUST.\n"
        f"- Are all surfaces in the output finished the same way as their "
        f"source (polished defaults to polished, no added brushed/matte)? They MUST be.\n"
        f"- Are decorative elements (pavé, prongs, side stones) symmetric "
        f"across both shoulders / both sides? They MUST be.\n"
        f"- Does decoration cover the SAME EXTENT as in the source (full-length "
        f"pavé stays full-length, not shrunk to shoulders only)? It MUST.\n"
        f"- Is the background pure white RGB(255,255,255) — not gray, cream, "
        f"or warm-tinted? It MUST be.\n"
        f"- Has any non-extracted component (e.g., the shank of Image 1 when "
        f"only its head was extracted) leaked into the output? It MUST NOT.\n"
        f"- Is the interior of the shank smooth and round (manufacturable, "
        f"wearable on a real finger)? It MUST be.\n"
        f"- Is the output clearly a NEW piece (not a copy of any single reference)? "
        f"It MUST be."
    )

    return "\n\n".join(sections)
