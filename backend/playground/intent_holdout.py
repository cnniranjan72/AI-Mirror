"""A third intent set, written after the classifier's errors were inspected.

Why this exists.

The 596-query benchmark is two very different halves. The 110 curated queries
score 100% - every single one - which is what a rule set scores against the
examples it was written from. The 486 synthetic queries, generated from ten
templates per class, score 77%. Reporting the blend as one number credits the
classifier with a generalisation it has not demonstrated.

Once the synthetic failures had been read, that half stopped being held out
either: any pattern added afterwards is informed by them. So these queries were
written fresh, by hand, to be answerable only from the same intuitions a person
would use - and deliberately in phrasings the two existing sets do not contain.

Rules for anything added here:

  - Never consult this set while changing the classifier. It is the estimate of
    whether a change generalises, and it is worth exactly as much as that
    separation.
  - Phrase naturally. The synthetic set already covers template phrasing; the
    value here is in the shapes a template would not produce.
  - Include the genuinely ambiguous ones, labelled the way a person would read
    them. A benchmark of easy cases measures nothing.
"""

HOLDOUT_DATASET = [
    # identity_question - the subject is the self, whatever frame it arrives in
    ("So what have you worked out about me so far?", "identity_question"),
    ("Paint me a picture of who I am", "identity_question"),
    ("If you had to sum me up in a sentence, what would you say?", "identity_question"),
    ("Am I the sort of person who finishes what they start?", "identity_question"),
    ("What would you say my blind spots are?", "identity_question"),
    ("Give me an honest read on my character", "identity_question"),
    ("Where do my priorities actually lie?", "identity_question"),
    ("What sort of viewer would you call me?", "identity_question"),

    # explanation - asks for a cause
    ("What's behind my drop-off in reading?", "explanation"),
    ("I don't get why cooking keeps coming up", "explanation"),
    ("Something changed last month - any idea what?", "explanation"),
    ("Account for the shift in what I watch at night", "explanation"),

    # comparison - sets two things against each other
    ("Am I watching more or less than I was in spring?", "comparison"),
    ("Set this month against last month for me", "comparison"),
    ("Which has grown more, chess or photography?", "comparison"),

    # prediction - asks about what is coming
    ("Where is this heading if nothing changes?", "prediction"),
    ("Will I still be into this in six months?", "prediction"),
    ("What's likely to fade next?", "prediction"),

    # recommendation - asks what to do
    ("Give me something worth trying next", "recommendation"),
    ("What would you steer me towards?", "recommendation"),
    ("Any suggestions for breaking the habit?", "recommendation"),

    # reflection - asks for a considered summary of a period
    ("Walk me through how my week went", "reflection"),
    ("Take stock of the last fortnight", "reflection"),
    ("How have I been doing lately?", "reflection"),

    # memory_question - asks what the system holds
    ("What do you actually have on file about me?", "memory_question"),
    ("Do you remember what I was into back in March?", "memory_question"),
    ("What have you kept from all this?", "memory_question"),

    # behavioral_question - asks about the behaviour itself
    ("How much of my time goes on this?", "behavioral_question"),
    ("When am I usually watching?", "behavioral_question"),
    ("How often do I come back to the same creators?", "behavioral_question"),

    # coaching - asks for help changing
    ("Help me spend less time on this", "coaching"),
    ("I want to build a better habit here - where do I start?", "coaching"),

    # information - genuinely about a thing, not about the self
    ("What does the confidence score actually mean?", "information"),
    ("How is a behaviour object put together?", "information"),

    # unknown - not answerable from behavioural data
    ("What's the weather doing tomorrow?", "unknown"),
    ("Book me a table for two", "unknown"),
]
