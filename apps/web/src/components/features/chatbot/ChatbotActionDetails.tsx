import { DocumentLinkRenderer } from "@components/features/message/renderers/DocumentLinkRenderer"
import { Badge } from "@components/ui/badge"
import { cn } from "@lib/utils"
import _ from "@lib/translate"
import { detailRows, documentNames } from "./actionCardModel"
import type { ChatbotAction } from "./types"

const PREVIEWED_DOCUMENTS = 3

/** What a card is about: the field rows (as the form shows them) and, for existing documents, their cards. */
export const ChatbotActionDetails = ({ action }: { action: ChatbotAction }) => {
    const rows = detailRows(action)
    const names = documentNames(action)
    // A document that does not exist yet is shown as the draft it would become.
    const isDraft = action.action === "Create" && names.length === 0
    const grid = rows.length > 0 && (
        <div className="grid grid-cols-[minmax(5rem,auto)_1fr] items-baseline gap-x-4 gap-y-1.5">
            {rows.map(({ label, value }) => (
                <div key={label} className="contents">
                    <span className="truncate text-p-sm text-ink-gray-5">{label}</span>
                    <span className="min-w-0 break-words text-p-sm text-ink-gray-8">{value}</span>
                </div>
            ))}
        </div>
    )
    return (
        <>
            {isDraft ? (
                <div className={cn("flex flex-col gap-2 rounded-md border border-dashed border-outline-gray-3 p-3")}>
                    <Badge variant="subtle" theme="gray" className="w-fit">{`${action.reference_doctype} · ${_("Draft")}`}</Badge>
                    {grid}
                </div>
            ) : grid}
            {names.slice(0, PREVIEWED_DOCUMENTS).map((name) => <DocumentLinkRenderer key={name} doctype={action.reference_doctype} docname={name} />)}
            {names.length > PREVIEWED_DOCUMENTS && <p className="text-xs text-ink-gray-5">{_("and {0} more", [String(names.length - PREVIEWED_DOCUMENTS)])}</p>}
        </>
    )
}
