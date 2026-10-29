import { describe, expect, it } from "vitest"
import { detailRows, documentNames, isDestructive, titleOf, verbOf } from "./actionCardModel"
import type { ChatbotAction } from "./types"

const card = (overrides: Partial<ChatbotAction> = {}): ChatbotAction => ({
    name: "a", action: "Delete", reference_doctype: "ToDo", names: '["T1","T2"]', values: "{}", details: '[{"label":"Status","value":"Open"}]',
    modified: "2026-10-29 10:00:00", status: "Pending", result: null, message_position: 1, ...overrides,
})

describe("actionCardModel", () => {
    it("marks only the hard-to-undo actions as destructive", () => {
        expect(["Delete", "Cancel", "Detach", "Unshare", "Unassign", "Untag"].every((action) => isDestructive(action as ChatbotAction["action"]))).toBe(true)
        expect(["Create", "Update", "Assign", "Tag", "Share", "Attach", "Submit"].some((action) => isDestructive(action as ChatbotAction["action"]))).toBe(false)
    })

    it("names the action on its button, not just Approve", () => {
        expect(verbOf("Cancel")).toBe("Cancel document")
        expect(verbOf("Tag")).toBe("Add tags")
    })

    it("counts the documents in the title only when there are several", () => {
        expect(titleOf("Delete", "ToDo", 1)).toBe("Delete ToDo")
        expect(titleOf("Delete", "ToDo", 3)).toBe("Delete 3 ToDo")
    })

    it("reads the rows and document names of a card", () => {
        expect(detailRows(card())).toEqual([{ label: "Status", value: "Open" }])
        expect(documentNames(card())).toEqual(["T1", "T2"])
        expect(detailRows(card({ details: "" }))).toEqual([])
    })
})
