import { ShieldQuestionIcon } from "lucide-react"
import { DocumentLinkRenderer } from "@components/features/message/renderers/DocumentLinkRenderer"
import { Badge } from "@components/ui/badge"
import { Button } from "@components/ui/button"
import _ from "@lib/translate"
import { useDecideChatbotAction } from "./useChatbotChat"
import type { ChatbotAction } from "./types"

const PREVIEWED_DOCUMENTS = 3

const OUTCOMES = {
    Approved: { theme: "green", label: "Approved" },
    Rejected: { theme: "gray", label: "Rejected" },
    Failed: { theme: "red", label: "Failed" },
} as const

interface ChatbotActionCardProps {
    chatId: string
    action: ChatbotAction
}

/** A change the AI wants to make but may not make alone. The user answers here; the card then stays, with the outcome. */
export const ChatbotActionCard = ({ chatId, action }: ChatbotActionCardProps) => {
    const { decide, loading } = useDecideChatbotAction(chatId)
    const names: string[] = JSON.parse(action.names)
    const outcome = action.status === "Pending" ? null : OUTCOMES[action.status]

    return (
        <div className="mx-4 my-2 ml-[3.75rem] flex max-w-xl flex-col gap-2 rounded-lg border border-outline-gray-2 bg-surface-white p-3">
            <div className="flex items-center gap-2 text-p-base font-medium text-ink-gray-8">
                <ShieldQuestionIcon className="size-4 text-ink-amber-3" />
                <span className="flex-1">{_("{0} {1}", [action.action, action.reference_doctype])}</span>
                {outcome && <Badge variant="subtle" theme={outcome.theme}>{_(outcome.label)}</Badge>}
            </div>
            {action.summary && <p className="text-p-sm text-ink-gray-7">{action.summary}</p>}
            {names.slice(0, PREVIEWED_DOCUMENTS).map((name) => <DocumentLinkRenderer key={name} doctype={action.reference_doctype} docname={name} />)}
            {names.length > PREVIEWED_DOCUMENTS && <p className="text-xs text-ink-gray-5">{_("and {0} more", [String(names.length - PREVIEWED_DOCUMENTS)])}</p>}
            {action.status === "Failed" && action.result && <p className="text-p-sm text-ink-red-3">{action.result}</p>}
            {!outcome && (
                <div className="flex gap-2">
                    <Button size="sm" disabled={loading} onClick={() => decide(action.name, true)}>{_("Approve")}</Button>
                    <Button size="sm" variant="outline" disabled={loading} onClick={() => decide(action.name, false)}>{_("Reject")}</Button>
                </div>
            )}
        </div>
    )
}
