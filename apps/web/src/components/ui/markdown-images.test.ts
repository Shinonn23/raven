import { describe, expect, it } from "vitest"
import { isAllowedImage } from "./markdown-images"

const origins = ["https://manual.example", "https://uat.manual.example"]

describe("isAllowedImage", () => {
    it("allows a picture on a manual site", () => {
        expect(isAllowedImage("https://manual.example/files/a.png", origins)).toBe(true)
        expect(isAllowedImage("https://uat.manual.example/files/b%20c.png?x=1", origins)).toBe(true)
    })

    it("refuses every other host, even one that looks alike", () => {
        expect(isAllowedImage("https://attacker.example/pixel.png?data=secret", origins)).toBe(false)
        expect(isAllowedImage("https://manual.example.attacker.example/a.png", origins)).toBe(false)
        expect(isAllowedImage("https://manual.example@attacker.example/a.png", origins)).toBe(false)
        expect(isAllowedImage("http://manual.example/a.png", origins)).toBe(false) // another scheme is another origin
    })

    it("refuses relative, data and script addresses and nothing at all", () => {
        for (const src of ["/files/a.png", "files/a.png", "data:image/png;base64,AAAA", "javascript:alert(1)", "", undefined]) {
            expect(isAllowedImage(src, origins)).toBe(false)
        }
    })

    it("allows nothing when no manual site is set up", () => {
        expect(isAllowedImage("https://manual.example/files/a.png", [])).toBe(false)
    })
})
