import { useState } from "react"
import { BotMessageSquareIcon, Share2Icon } from "lucide-react"
import { Button } from "@components/ui/button"
import { useUserCookieData } from "@hooks/useUserCookieData"
import { useUser } from "@hooks/useUser"
import _ from "@lib/translate"
import { ChatbotShareDialog } from "./ChatbotShareDialog"
import type { ChatbotChat } from "./types"

/** The thin title bar every Raven conversation has (same height, border and type as the channel header). */
export const ChatbotHeader = ({ title, chat }: { title?: string; chat?: ChatbotChat }) => {
    const { name: currentUser } = useUserCookieData()
    const owner = useUser(chat?.owner)
    const [isSharing, setIsSharing] = useState(false)
    const isOwner = chat?.owner === currentUser

    return (
        <div className="flex h-11 w-full shrink-0 items-center justify-between gap-2 border-b border-outline-gray-2 bg-surface-base px-3">
            <div className="flex min-w-0 items-center gap-1.5">
                <BotMessageSquareIcon className="size-4.5 shrink-0 text-ink-gray-6 md:size-4" />
                <span className="truncate text-lg font-medium md:text-sm">{title ?? _("New chat")}</span>
                {chat && !isOwner && <span className="shrink-0 text-xs text-ink-gray-5">{_("Shared by {0}", [owner?.full_name || chat.owner])}</span>}
            </div>
            {chat && isOwner && (
                <>
                    <Button variant="ghost" size="sm" onClick={() => setIsSharing(true)}><Share2Icon />{_("Share")}</Button>
                    <ChatbotShareDialog chatId={chat.name} open={isSharing} onOpenChange={setIsSharing} />
                </>
            )}
        </div>
    )
}
