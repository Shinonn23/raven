import { useState } from "react"
import dayjs from "dayjs"
import { ChevronDownIcon, ChevronRightIcon, CircleCheckIcon, CircleXIcon, ShieldQuestionIcon, TriangleAlertIcon } from "lucide-react"
import { Badge } from "@components/ui/badge"
import { Button } from "@components/ui/button"
import _ from "@lib/translate"
import { documentNames, isDestructive, titleOf, verbOf } from "./actionCardModel"
import { ChatbotActionDetails } from "./ChatbotActionDetails"
import { useDecideChatbotAction } from "./useChatbotChat"
import type { ChatbotAction } from "./types"

const OUTCOMES = {
    Approved: { theme: "green", icon: <CircleCheckIcon className="size-4 text-ink-green-8" />, label: "Approved" },
    Rejected: { theme: "gray", icon: <CircleXIcon className="size-4 text-ink-gray-5" />, label: "Rejected" },
    Failed: { theme: "red", icon: <TriangleAlertIcon className="size-4 text-ink-red-3" />, label: "Failed" },
} as const

const CARD = "mx-4 my-2 ml-[3.75rem] max-w-xl rounded-lg border border-outline-gray-2 bg-surface-white"

interface ChatbotActionCardProps {
    chatId: string
    action: ChatbotAction
}

/** A change the AI wants to make but may not make alone. It waits as a full card; once answered it shrinks to one line with the outcome. */
export const ChatbotActionCard = ({ chatId, action }: ChatbotActionCardProps) => {
    const title = titleOf(_(verbOf(action.action)), action.reference_doctype, documentNames(action).length)
    return action.status === "Pending"
        ? <PendingCard chatId={chatId} action={action} title={title} />
        : <DecidedCard action={action} title={title} />
}

const PendingCard = ({ chatId, action, title }: ChatbotActionCardProps & { title: string }) => {
    const { decide, busy } = useDecideChatbotAction(chatId)
    return (
        <div className={`${CARD} flex flex-col gap-3 p-3`}>
            <div className="flex items-center gap-2 text-p-base font-medium text-ink-gray-8">
                <ShieldQuestionIcon className="size-4 text-ink-amber-3" />{title}
            </div>
            <ChatbotActionDetails action={action} />
            <div className="flex gap-2">
                <Button size="sm" theme={isDestructive(action.action) ? "red" : "gray"} disabled={busy} onClick={() => decide(action.name, true)}>{_(verbOf(action.action))}</Button>
                <Button size="sm" variant="outline" disabled={busy} onClick={() => decide(action.name, false)}>{_("Reject")}</Button>
            </div>
        </div>
    )
}

const DecidedCard = ({ action, title }: { action: ChatbotAction; title: string }) => {
    const [open, setOpen] = useState(false)
    const outcome = OUTCOMES[action.status as keyof typeof OUTCOMES]
    return (
        <div className={`${CARD} overflow-hidden`}>
            <button type="button" aria-expanded={open} onClick={() => setOpen((value) => !value)}
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-p-sm text-ink-gray-7 hover:bg-surface-gray-1">
                {outcome.icon}
                <span className="font-medium text-ink-gray-8">{title}</span>
                {action.status === "Approved" && action.result && <span className="min-w-0 flex-1 truncate text-ink-gray-5">{action.result}</span>}
                {action.status !== "Approved" && <span className="flex-1" />}
                <span className="shrink-0 text-xs text-ink-gray-4">{dayjs(action.modified).format("hh:mm a")}</span>
                <Badge variant="subtle" theme={outcome.theme}>{_(outcome.label)}</Badge>
                {open ? <ChevronDownIcon className="size-4 shrink-0" /> : <ChevronRightIcon className="size-4 shrink-0" />}
            </button>
            {open && (
                <div className="flex flex-col gap-3 border-t border-outline-gray-2 p-3">
                    {action.status === "Failed" && action.result && <p className="text-p-sm text-ink-red-3">{action.result}</p>}
                    <ChatbotActionDetails action={action} />
                </div>
            )}
        </div>
    )
}
