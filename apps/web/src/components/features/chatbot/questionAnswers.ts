export type AskedOption = { label: string; description?: string; preview?: string }
export type AskedQuestion = { question: string; options: AskedOption[]; multiple?: boolean }

/** The choices are laid out as a list with a preview beside it when any of them has a preview or a description. */
export const hasDetails = (question: AskedQuestion): boolean => question.options.some((option) => option.preview || option.description)

/** What the user has picked or typed for each question so far. */
export type Draft = { picked: string[]; typed: string }

export const emptyDraft: Draft = { picked: [], typed: "" }

/** A question's answer: the chosen options and the user's own words, or "" when they have given none. */
export const answerOf = ({ picked, typed }: Draft): string => [...picked, typed.trim()].filter(Boolean).join(", ")

/** Pick an option. A single-choice question keeps one pick, and picking again drops it; picking clears what was typed. */
export const togglePick = (draft: Draft, option: string, multiple: boolean): Draft => {
    const already = draft.picked.includes(option)
    if (multiple) return { ...draft, picked: already ? draft.picked.filter((other) => other !== option) : [...draft.picked, option] }
    return { picked: already ? [] : [option], typed: "" }
}

/** Typing an own answer to a single-choice question replaces the pick. */
export const type = (draft: Draft, typed: string, multiple: boolean): Draft => ({ picked: multiple ? draft.picked : [], typed })

export const allAnswers = (questions: AskedQuestion[], drafts: Draft[]): string[] => questions.map((_, index) => answerOf(drafts[index] ?? emptyDraft))

/** Every question has an answer, so the user may send. */
export const isComplete = (questions: AskedQuestion[], drafts: Draft[]): boolean => allAnswers(questions, drafts).every(Boolean)
