import type { ChatbotSkill } from "./types"

export type MarkdownFormat = "bold" | "italic" | "code" | "list" | "quote"

export type TextEdit = { value: string; selectionStart: number; selectionEnd: number }

const WRAPPERS: Record<"bold" | "italic" | "code", string> = { bold: "**", italic: "_", code: "`" }
const LINE_PREFIXES: Record<"list" | "quote", string> = { list: "- ", quote: "> " }

/** Applies a markdown format to the selected text (or to its lines for list / quote). */
export const applyMarkdownFormat = (edit: TextEdit, format: MarkdownFormat): TextEdit => {
    const { value, selectionStart: start, selectionEnd: end } = edit
    if (format === "list" || format === "quote") {
        const lineStart = value.lastIndexOf("\n", start - 1) + 1
        const prefixed = value.slice(lineStart, end).split("\n").map((line) => LINE_PREFIXES[format] + line).join("\n")
        const nextValue = value.slice(0, lineStart) + prefixed + value.slice(end)
        return { value: nextValue, selectionStart: lineStart, selectionEnd: lineStart + prefixed.length }
    }
    const wrapper = WRAPPERS[format]
    const nextValue = value.slice(0, start) + wrapper + value.slice(start, end) + wrapper + value.slice(end)
    return { value: nextValue, selectionStart: start + wrapper.length, selectionEnd: end + wrapper.length }
}

/** The slash-command text being typed at the start of the draft, e.g. "/rep" → "rep"; null otherwise. */
export const slashQuery = (draft: string): string | null => /^\/([a-z0-9-]*)$/i.exec(draft)?.[1] ?? null

/** Skills matching what follows the "/" — company skills first, then the user's own. */
export const matchingSkills = (skills: ChatbotSkill[], query: string) =>
    skills.filter((skill) => skill.command.startsWith(query.toLowerCase()) || skill.title.toLowerCase().includes(query.toLowerCase()))

