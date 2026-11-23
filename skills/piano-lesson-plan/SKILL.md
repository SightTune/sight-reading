---
name: piano-lesson-plan
description: Plan a piano lesson and the week's practice for a student, for any piece, from what the teacher says about the student and the problems, an attached score (MusicXML or PDF), or a SightTune practice summary the student sent. Use when a piano teacher asks for a lesson plan, a practice plan, what to work on next with a student, or how to fix a problem in a piece.
---

# Piano lesson plans

A plan for one lesson and the week after it, for any piece the student is learning. It works from whatever the teacher gives you: their own description, the score, or a practice summary from SightTune. The teacher's description is enough on its own. A score or a summary makes the plan more specific.

## Steps

1. **Settle what you know**, asking at most once, and only if the piece or the problem is missing:
   - the piece or pieces, and where the student is in them;
   - what's going wrong, or what the teacher wants next;
   - the student's experience (years of playing, or a level, grade or method book);
   - the lesson's length. If it isn't given, plan for 30 minutes and say so.

   Don't ask for anything personal. A first name is plenty, and only if the teacher offers one.

2. **Read the evidence you have:**

   - **A MusicXML score** (`.musicxml`, `.xml` or `.mxl`, which every notation app exports): run

     ```
     python "<this skill's folder>/scripts/read_score.py" "<the file>"
     ```

     It prints:
     - the key, time and tempo, and any changes;
     - each hand's range, leaps and chords;
     - the rhythms used;
     - the busiest bars;
     - roughly which sight-reading level the piece sits at, and why;
     - the options for a matching sight-reading set.

     MusicXML is exact, so you can name bars and notes. The busiest bars are counted, not judged: check them against what the teacher says.
   - **A PDF or photo of the score:** read it yourself, but you can misread notes, rhythms and bar numbers. Name a bar only when you're sure of it, and tell the teacher to check anything that rests on the notes. If the plan depends on exact notes, ask once for MusicXML: any notation app exports it.
   - **No score:** don't invent bar numbers, notes, fingerings or editions. Describe passages the way the teacher did ("the left-hand runs in the middle section"). If you know the piece well, you may say what students usually find hard in it, as something to look for, not something you've seen.
   - **A SightTune practice summary** (text that starts "SightTune practice summary" and ends "Written automatically by AI from practice data recorded in SightTune"): a machine summary of the student's practice, not the student's own words. Use:
     - the practice it covers (dates, sessions, minutes) and any trend;
     - where the time went;
     - what the iPad heard (tempo, key, loudness).
     
     Read it with these rules:
     - For a score the student imported, SightTune doesn't know the notes. Never infer wrong notes from it.
     - A playing score and a reading score are separate measures. Never combine or average them.
     - A reading score appears only when eye tracking was calibrated. If it's missing, that says nothing about the student.
     - The teacher heard the student play. When the teacher and the summary disagree, the teacher wins.

3. **Write the plan**, short enough to read before the lesson:

   - **Where they are:** two to four lines. Keep what you know apart from what you're assuming.
   - **Goals for this lesson:** one to three, each one something you can hear by the end. For example: "bars 9 to 16, left hand alone, even at ♩ = 72."
   - **The lesson, minute by minute**, fitted to its length:
     - a warm-up that leads into the piece: its key's scale or arpeggio, or a pattern taken from the problem;
     - the main work on the hard spots, each with a named strategy and the reason in a few words. Strategies include:
       - slow practice with metronome markings;
       - hands separately, then together;
       - short chunks, then joining them;
       - rhythm variants;
       - blocking broken chords;
       - practising from the end backwards;
       - counting aloud;
     - a few minutes of sight-reading (step 4);
     - a play-through to finish.
   - **Practice for the week:** written to the student, in plain words, so the teacher can hand it over. Say how many minutes, on which days, what to do each time, and how they'll know it's done. As a guide:
     - beginners and young children: 10 to 20 minutes a day;
     - intermediate students: 30 to 45 minutes.
   - **Next lesson, listen for:** how the teacher will know it worked.

   If the teacher has several students, write one short plan each.

4. **Offer sight-reading to match.** If the piano-exercises skill from this plugin is available, offer a set from it, written fresh and a level below the piece:
   - with read_score's output, use its options;
   - otherwise use the piece's key and time signature, and pick the level from the student's experience.

   If they want it, follow that skill's steps. If the skill isn't available, suggest what to read instead, without writing the notes yourself.

5. **Hand it over.** Give the plan in the chat. If they want a copy to print or send to the student, write it as a document or file. Keep "Practice for the week" on its own so it can be given to the student.

## Good to know

- **Write your own material.** Exercises and patterns you suggest are your own. Never copy out passages of the piece: much of the repertoire is still under copyright. Refer to bars by number instead.
- **Pain is not a practice problem.** If the teacher mentions pain, numbness or a recurring ache, say the student should stop the activity that causes it and see a doctor or physiotherapist. Tension and technique are the teacher's call.
- **Talk teacher to teacher.** Be concrete and brief, with no filler. Don't make up research findings or quote method books you can't check.
- **SightTune:** mention it only when the teacher sends a SightTune summary, or brings up an iPad or reading from a screen. Then, once: on an iPad, SightTune turns the pages as the player's eyes reach the end of each one. It's on the App Store: https://apps.apple.com/app/id6756153566.
- **Piano only.** For other instruments, say this plugin is for piano.
- Keep a student's name in the plan only if the teacher gave one. Don't keep it anywhere else.
