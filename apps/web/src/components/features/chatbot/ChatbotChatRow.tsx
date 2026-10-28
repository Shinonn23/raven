import { useState } from "react"
import { NavLink, useNavigate } from "react-router-dom"
import { MoreHorizontalIcon, PencilIcon, Trash2Icon } from "lucide-react"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@components/ui/dropdown-menu"
import { useUserCookieData } from "@hooks/useUserCookieData"
import { cn } from "@lib/utils"
import _ from "@lib/translate"
import { ChatbotNameDialog } from "./ChatbotNameDialog"
import { useChatbot } from "./useChatbot"
import type { ChatbotChatSummary } from "./types"

/** A sidebar chat link in the DM list's row style; the "…" menu (rename / delete) appears on hover. */
export const ChatbotChatRow = ({ chat, indented }: { chat: ChatbotChatSummary; indented?: boolean }) => {
    const { renameChat, deleteChat } = useChatbot()
    const navigate = useNavigate()
    const isOwner = chat.owner === useUserCookieData().name
    const [isRenaming, setIsRenaming] = useState(false)

    const remove = async () => {
        await deleteChat(chat.name)
        navigate("/chatbot")
    }

    return (
        <>
            <NavLink to={`/chatbot/${chat.name}`} className={cn("block px-2 py-0.5", indented && "ps-6")}>
                {({ isActive }) => (
                    <div className={cn(
                        "group/row flex w-full select-none items-center gap-2 rounded px-2 py-2 text-sm text-ink-gray-8 transition-colors hover:bg-surface-gray-3",
                        isActive && "bg-surface-elevation-3 shadow-sm hover:bg-surface-elevation-3",
                    )}>
                        <span className="min-w-0 flex-1 truncate leading-snug">{chat.title}</span>
                        {isOwner && <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                                <button type="button" aria-label={_("Chat options")} onClick={(event) => event.preventDefault()}
                                    className="invisible shrink-0 text-ink-gray-5 hover:text-ink-gray-9 group-hover/row:visible data-[state=open]:visible">
                                    <MoreHorizontalIcon className="size-4" />
                                </button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="start">
                                <DropdownMenuItem onSelect={() => setIsRenaming(true)}><PencilIcon />{_("Rename")}</DropdownMenuItem>
                                <DropdownMenuItem onSelect={remove}><Trash2Icon />{_("Delete")}</DropdownMenuItem>
                            </DropdownMenuContent>
                        </DropdownMenu>}
                    </div>
                )}
            </NavLink>
            <ChatbotNameDialog
                open={isRenaming}
                onOpenChange={setIsRenaming}
                title={_("Rename chat")}
                label={_("Chat name")}
                submitLabel={_("Rename")}
                initialName={chat.title}
                onSubmit={(title) => renameChat(chat.name, title)}
            />
        </>
    )
}
