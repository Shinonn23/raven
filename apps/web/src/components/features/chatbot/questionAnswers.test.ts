import { describe, expect, it } from "vitest"
import { allAnswers, answerOf, emptyDraft, hasAnyAnswer, hasDetails, hasPreview, nextToAnswer, togglePick, type } from "./questionAnswers"

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

    it("lets the user send once any question has an answer", () => {
        const questions = [{ question: "One?", options: [{ label: "A" }] }, { question: "Two?", options: [] }]
        expect(hasAnyAnswer(questions, [])).toBe(false)
        expect(hasAnyAnswer(questions, [emptyDraft, type(emptyDraft, "text", false)])).toBe(true)
        expect(allAnswers(questions, [togglePick(emptyDraft, "A", false)])).toEqual(["A", ""])
    })

    it("goes to the next question still without an answer", () => {
        const questions = ["a", "b", "c"].map((question) => ({ question, options: [] }))
        const answered = type(emptyDraft, "x", false)
        expect(nextToAnswer(questions, [emptyDraft, emptyDraft, emptyDraft], 0)).toBe(1)
        expect(nextToAnswer(questions, [emptyDraft, answered, emptyDraft], 0)).toBe(2)
        expect(nextToAnswer(questions, [emptyDraft, answered, answered], 0)).toBe(1)
        expect(nextToAnswer(questions, [emptyDraft, emptyDraft, emptyDraft], 2)).toBe(2)
    })

    it("has a preview pane only when a choice has a preview", () => {
        expect(hasPreview({ question: "?", options: [{ label: "A", description: "only a description" }] })).toBe(false)
        expect(hasPreview({ question: "?", options: [{ label: "A", preview: "**A**" }] })).toBe(true)
    })

    it("shows a preview layout only for questions whose choices have details", () => {
        expect(hasDetails({ question: "?", options: [{ label: "A" }] })).toBe(false)
        expect(hasDetails({ question: "?", options: [{ label: "A" }, { label: "B", preview: "**B**" }] })).toBe(true)
        expect(hasDetails({ question: "?", options: [{ label: "A", description: "first" }] })).toBe(true)
    })
})
