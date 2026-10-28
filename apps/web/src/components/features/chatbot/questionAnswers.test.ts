import { describe, expect, it } from "vitest"
import { allAnswers, answerOf, emptyDraft, isComplete, togglePick, type } from "./questionAnswers"

describe("questionAnswers", () => {
    it("keeps one pick for a single-choice question, and picking it again drops it", () => {
        const first = togglePick(emptyDraft, "A", false)
        expect(togglePick(first, "B", false).picked).toEqual(["B"])
        expect(togglePick(first, "A", false).picked).toEqual([])
    })

    it("collects several picks for a multiple-choice question", () => {
        const draft = togglePick(togglePick(emptyDraft, "A", true), "B", true)
        expect(answerOf(draft)).toBe("A, B")
        expect(answerOf(togglePick(draft, "A", true))).toBe("B")
    })

    it("lets the user's own words replace a single pick and add to several", () => {
        expect(answerOf(type(togglePick(emptyDraft, "A", false), "my own", false))).toBe("my own")
        expect(answerOf(type(togglePick(emptyDraft, "A", true), " my own ", true))).toBe("A, my own")
        expect(togglePick(type(emptyDraft, "typed", false), "A", false)).toEqual({ picked: ["A"], typed: "" })
    })

    it("is complete only when every question has an answer", () => {
        const questions = [{ question: "One?", options: ["A"] }, { question: "Two?", options: [] }]
        expect(isComplete(questions, [togglePick(emptyDraft, "A", false)])).toBe(false)
        const drafts = [togglePick(emptyDraft, "A", false), type(emptyDraft, "text", false)]
        expect(isComplete(questions, drafts)).toBe(true)
        expect(allAnswers(questions, drafts)).toEqual(["A", "text"])
    })
})
