import { describe, expect, it } from "vitest"
import { effortLabel, resolveChoice, withEffort, type ChatbotModelOption } from "./chatbotChoice"

const options: ChatbotModelOption[] = [
    { model: "big", efforts: ["low", "high"] },
    { model: "mid", efforts: ["low", "medium", "high"] },
    { model: "plain", efforts: [] },
]

describe("resolveChoice", () => {
    it("has nothing to choose when the admin allows no models", () => {
        expect(resolveChoice([], { model: "mid", effort: "low" })).toBeUndefined()
    })

    it("defaults to the first model, with its first effort when medium is not offered", () => {
        expect(resolveChoice(options)).toEqual({ model: "big", effort: "low" })
    })

    it("prefers medium when the model offers it", () => {
        expect(resolveChoice(options, { model: "mid" })).toEqual({ model: "mid", effort: "medium" })
    })

    it("keeps the user's last pick while it is still allowed", () => {
        expect(resolveChoice(options, { model: "mid", effort: "high" })).toEqual({ model: "mid", effort: "high" })
    })

    it("falls back when the admin removed the model or the effort", () => {
        expect(resolveChoice(options, { model: "gone", effort: "high" })).toEqual({ model: "big", effort: "low" })
        expect(resolveChoice(options, { model: "mid", effort: "max" })).toEqual({ model: "mid", effort: "medium" })
    })

    it("gives a model without efforts no effort", () => {
        expect(resolveChoice(options, { model: "plain", effort: "high" })).toEqual({ model: "plain", effort: undefined })
    })
})

describe("effortLabel", () => {
    it("names known efforts and passes unknown ones through", () => {
        expect(effortLabel("xhigh")).toBe("Extra high")
        expect(effortLabel("custom")).toBe("custom")
    })
})

describe("withEffort", () => {
    it("changes the effort of the choice in use, even if nothing was stored yet", () => {
        const inUse = resolveChoice(options)
        expect(withEffort(inUse, "high")).toEqual({ model: "big", effort: "high" })
    })

    it("has nothing to change without a choice", () => {
        expect(withEffort(undefined, "high")).toBeUndefined()
    })
})
