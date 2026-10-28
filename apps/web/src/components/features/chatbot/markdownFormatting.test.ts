import { describe, expect, it } from "vitest"
import { applyMarkdownFormat, slashQuery } from "./markdownFormatting"

describe("applyMarkdownFormat", () => {
    it("wraps the selection", () => {
        const result = applyMarkdownFormat({ value: "make bold now", selectionStart: 5, selectionEnd: 9 }, "bold")
        expect(result.value).toBe("make **bold** now")
        expect(result.value.slice(result.selectionStart, result.selectionEnd)).toBe("bold")
    })

    it("inserts an empty pair at the cursor", () => {
        const result = applyMarkdownFormat({ value: "ab", selectionStart: 1, selectionEnd: 1 }, "code")
        expect(result.value).toBe("a``b")
        expect(result.selectionStart).toBe(2)
    })

    it("prefixes every selected line for lists", () => {
        const result = applyMarkdownFormat({ value: "x\none\ntwo", selectionStart: 2, selectionEnd: 9 }, "list")
        expect(result.value).toBe("x\n- one\n- two")
    })
})

describe("slashQuery", () => {
    it("reads a command being typed at the start", () => {
        expect(slashQuery("/")).toBe("")
        expect(slashQuery("/weekly-re")).toBe("weekly-re")
    })

    it("ignores slashes elsewhere or after a space", () => {
        expect(slashQuery("hello /x")).toBeNull()
        expect(slashQuery("/x y")).toBeNull()
    })
})
