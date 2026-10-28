import { Outlet, useMatch } from "react-router-dom"
import { ChatbotSidebar } from "@components/features/chatbot/ChatbotSidebar"
import AppMobileFooter from "@components/features/header/AppMobileFooter"
import { useChatbotStream } from "@components/features/chatbot/useChatbotStream"
import { cn } from "@lib/utils"

/** Chatbot module layout: permanent sidebar beside the conversation, framed like Direct Messages. */
export default function Chatbot() {
    // Mobile is stacked: the sidebar is the page, an open chat replaces it.
    useChatbotStream()
    const isChatOpen = Boolean(useMatch("/chatbot/:id"))

    return (
        <div className="relative flex h-full min-h-0 w-full flex-col">
            <div className="flex min-h-0 flex-1">
                <div className={cn("min-h-0 w-full shrink-0 md:w-(--dm-sidebar-width)", isChatOpen && "max-md:hidden")}>
                    <ChatbotSidebar />
                </div>
                <div className={cn("min-h-0 min-w-0 flex-1 flex-col bg-surface-gray-1", isChatOpen ? "flex" : "max-md:hidden md:flex")}>
                    <Outlet />
                </div>
            </div>
            <AppMobileFooter inert={isChatOpen ? true : undefined} />
        </div>
    )
}
