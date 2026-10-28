import { describe, expect, it } from "vitest"
import { pastedFiles } from "./pastedFiles"

const clipboard = (files: File[], text = "") => ({ files: files as unknown as FileList, getData: () => text })
const NOW = new Date("2026-10-28T21:55:30Z")

describe("pastedFiles", () => {
    it("returns nothing without a clipboard", () => expect(pastedFiles(null)).toEqual([]))

    it("takes the picture when there is no text", () => {
        const picture = new File(["x"], "report.png", { type: "image/png" })
        expect(pastedFiles(clipboard([picture]), NOW)).toEqual([picture])
    })

    it("leaves a paste that carries text alone", () => {
        expect(pastedFiles(clipboard([new File(["x"], "image.png")], "A1\tB1"), NOW)).toEqual([])
    })

    it("gives screenshots called image.png their own names", () => {
        const names = pastedFiles(clipboard([new File(["x"], "image.png", { type: "image/png" }), new File(["y"], "image.png", { type: "image/png" })]), NOW).map((file) => file.name)
        expect(names).toEqual(["pasted-image-20261028215530.png", "pasted-image-20261028215530-2.png"])
    })
})
