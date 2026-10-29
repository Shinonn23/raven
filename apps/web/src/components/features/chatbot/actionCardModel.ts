import type { ChatbotAction } from "./types"

/** What each action is called on its button (translate it where it is shown), and whether it is hard to undo (the button is then red). */
const ACTIONS: Record<ChatbotAction["action"], { verb: string; destructive: boolean }> = {
    Create: { verb: "Create", destructive: false },
    Update: { verb: "Update", destructive: false },
    Assign: { verb: "Assign", destructive: false },
    Unassign: { verb: "Remove assignment", destructive: true },
    Tag: { verb: "Add tags", destructive: false },
    Untag: { verb: "Remove tags", destructive: true },
    Share: { verb: "Share", destructive: false },
    Unshare: { verb: "Stop sharing", destructive: true },
    Attach: { verb: "Attach", destructive: false },
    Detach: { verb: "Remove attachment", destructive: true },
    Submit: { verb: "Submit", destructive: false },
    Cancel: { verb: "Cancel document", destructive: true },
    Delete: { verb: "Delete", destructive: true },
}

export const verbOf = (action: ChatbotAction["action"]) => ACTIONS[action].verb
export const isDestructive = (action: ChatbotAction["action"]) => ACTIONS[action].destructive

/** "Delete ToDo", or "Delete 3 ToDo" when it is for several documents. */
export const titleOf = (verb: string, doctype: string, count: number) => (count > 1 ? `${verb} ${count} ${doctype}` : `${verb} ${doctype}`)

export type DetailRow = { label: string; value: string }
export const detailRows = (action: ChatbotAction): DetailRow[] => JSON.parse(action.details || "[]")
export const documentNames = (action: ChatbotAction): string[] => JSON.parse(action.names || "[]")
