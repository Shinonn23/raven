import { describe, expect, it } from "vitest"
import { buildItems, COLUMNS, isImageFile, sourcesFor, stepIndex, stepSource } from "./attachPickerItems"
import type { SystemFile } from "./types"

const file = (name: string): SystemFile => ({ name, file_name: name, file_url: `/files/${name}`, file_size: 1, creation: "" })
const documents = [{ doctype: "Sales Order", docname: "SO-0001" }, { doctype: "Customer", docname: "Acme" }]

describe("sourcesFor", () => {
    it("offers Documents only when documents are provided", () => {
        expect(sourcesFor(false)).toEqual(["all", "files", "upload"])
        expect(sourcesFor(true)).toContain("documents")
    })
})

describe("stepSource", () => {
    it("wraps in both directions", () => {
        const sources = sourcesFor(false)
        expect(stepSource(sources, "upload", 1)).toBe("all")
        expect(stepSource(sources, "all", -1)).toBe("upload")
    })
})

describe("buildItems", () => {
    it("All lists upload, files and documents in order", () => {
        const kinds = buildItems("all", [file("a.pdf")], documents, "").map((item) => item.kind)
        expect(kinds).toEqual(["upload", "file", "document", "document"])
    })

    it("Files and Upload show only their own rows", () => {
        expect(buildItems("files", [file("a.pdf")], documents, "").map((item) => item.kind)).toEqual(["file"])
        expect(buildItems("upload", [file("a.pdf")], documents, "").map((item) => item.kind)).toEqual(["upload"])
    })

    it("filters documents by the search text", () => {
        const items = buildItems("documents", [], documents, "acme")
        expect(items).toHaveLength(1)
        expect(items[0].id).toBe("Customer/Acme")
    })
})

describe("isImageFile", () => {
    it("recognises images by extension, ignoring case", () => {
        expect(isImageFile("Photo.JPG")).toBe(true)
        expect(isImageFile("report.pdf")).toBe(false)
        expect(isImageFile("noextension")).toBe(false)
    })
})

describe("stepIndex", () => {
    it("moves a whole row in card views and stays put at the edges", () => {
        expect(stepIndex(1, 1, COLUMNS.cards, 8)).toBe(4)
        expect(stepIndex(4, -1, COLUMNS.cards, 8)).toBe(1)
        expect(stepIndex(6, 1, COLUMNS.cards, 8)).toBe(6)
        expect(stepIndex(0, -1, COLUMNS.list, 8)).toBe(0)
    })
})
