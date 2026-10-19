"""AI assistant. Uses Groq (OpenAI-compatible API) if GROQ_API_KEY is set, otherwise a built-in FAQ fallback."""
import os
import httpx

SYSTEM = """You are DefectEye Assistant, helping a quality engineer use a computer-vision inspection system for
car parts and lenses. It detects: scrap/flash (excess plastic), gate-cut remnants (leftover injection-mould
gate stubs) and fingerprints on lenses. Decisions: PASS (release), REWORK (trim gate / clean lens, re-inspect),
RECYCLE (scrap -> regrind). Answer briefly and practically. Today's stats: {stats}"""

FAQ = [
    (("gate",), "A gate cut is the leftover stub where molten plastic entered the mould. A small stub is trimmed (REWORK); a large one means RECYCLE."),
    (("scrap", "flash"), "Scrap/flash is thin excess material squeezed out at the mould parting line. Any flash makes the part RECYCLE in this system. Frequent flash usually means worn mould or too much injection pressure."),
    (("finger", "lens", "smudge"), "Fingerprints on lenses are oily smudges. They are detected as ridge-like texture on a smooth surface. The part goes to REWORK: clean it and re-inspect. Use gloves to avoid repeats."),
    (("recycle", "regrind"), "RECYCLE parts have defects that cannot be fixed. They are reground and mixed back into raw material at a controlled percentage."),
    (("rework",), "REWORK means a fixable minor defect: trim the gate stub or clean the lens, then inspect again."),
    (("pdf", "report"), "Click 'Download Daily PDF Report'. It lists totals, decisions, defect counts and flagged parts for supervisor sign-off."),
    (("verify", "verified"), "'Verified' counts parts where an operator confirmed the AI decision using the Confirm button."),
    (("count", "total", "how many", "checked"), None),
]


GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


async def reply(message, stats):
    key = os.getenv("GROQ_API_KEY")
    if key:
        try:
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.post(GROQ_URL,
                                 headers={"Authorization": f"Bearer {key}"},
                                 json={"model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                                       "max_tokens": 500, "temperature": 0.4,
                                       "messages": [{"role": "system", "content": SYSTEM.format(stats=stats)},
                                                    {"role": "user", "content": message}]})
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
            print("Groq API error:", r.status_code, r.text[:300])   # shows in the VS Code terminal
        except Exception as e:  # fall through to FAQ
            print("Groq request failed:", e)
    m = message.lower()
    for keys, ans in FAQ:
        if any(k in m for k in keys):
            return ans or (f"Today: {stats['checked']} checked, {stats['verified']} verified, {stats['PASS']} pass, "
                           f"{stats['REWORK']} rework, {stats['RECYCLE']} recycle.")
    return ("I can explain gate cuts, scrap/flash, lens fingerprints, decisions, counts and the PDF report. "
            "(Set GROQ_API_KEY to unlock open-ended answers.)")
