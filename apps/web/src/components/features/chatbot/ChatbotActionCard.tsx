import { ShieldQuestionIcon } from "lucide-react"
import { Button } from "@components/ui/button"
import _ from "@lib/translate"
import { useDecideChatbotAction } from "./useChatbotChat"
import type { ChatbotPendingAction } from "./types"

interface ChatbotActionCardProps {
    chatId: string
    action: ChatbotPendingAction
}

/** A change the AI wants to make but may not make alone: the user approves or rejects it here. */
export const ChatbotActionCard = ({ chatId, action }: ChatbotActionCardProps) => {
    const { decide, loading } = useDecideChatbotAction(chatId)
    const names: string[] = JSON.parse(action.names)

    return (
        <div className="mx-4 my-2 ml-[3.75rem] flex max-w-xl flex-col gap-2 rounded-lg border border-outline-gray-2 bg-surface-white p-3">
            <div className="flex items-center gap-2 text-p-base font-medium text-ink-gray-8">
                <ShieldQuestionIcon className="size-4 text-ink-amber-3" />
                {_("{0} {1}", [action.action, action.reference_doctype])}
            </div>
            <p className="text-p-sm text-ink-gray-7">{action.summary}</p>
            <p className="break-words text-xs text-ink-gray-5">{names.slice(0, 5).join(", ")}{names.length > 5 ? _(" and {0} more", [String(names.length - 5)]) : ""}</p>
            <div className="flex gap-2">
                <Button size="sm" disabled={loading} onClick={() => decide(action.name, true)}>{_("Approve")}</Button>
                <Button size="sm" variant="outline" disabled={loading} onClick={() => decide(action.name, false)}>{_("Reject")}</Button>
            </div>
        </div>
    )
}
