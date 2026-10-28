import { useAtomValue } from "jotai"
import { useNavigate, useParams, useSearchParams } from "react-router-dom"
import { Island } from "@components/layout/Island"
import { Skeleton } from "@components/ui/skeleton"
import { ChatbotComposer } from "@components/features/chatbot/ChatbotComposer"
import { ChatbotHeader } from "@components/features/chatbot/ChatbotHeader"
import { ChatbotMessages } from "@components/features/chatbot/ChatbotMessages"
import { useChatbot } from "@components/features/chatbot/useChatbot"
import { chatbotStatusAtom, chatbotStreamsAtom } from "@components/features/chatbot/useChatbotStream"
import { useChatbotChat, useSendChatbotMessage } from "@components/features/chatbot/useChatbotChat"
import type { ChatbotOutgoingMessage } from "@components/features/chatbot/types"

/** `/chatbot/new` (also `/chatbot`) starts a chat, optionally in `?project=`; `/chatbot/:id` continues one. Laid out like a channel. */
export default function ChatbotConversation() {
    const { id } = useParams()
    const chatId = id === "new" ? undefined : id
    const projectId = useSearchParams()[0].get("project")
    const { projects } = useChatbot()
    const { chat, isLoading } = useChatbotChat(chatId)
    const { send, pendingText } = useSendChatbotMessage()
    const navigate = useNavigate()
    const streamingText = useAtomValue(chatbotStreamsAtom)[chatId ?? ""] ?? null
    const status = useAtomValue(chatbotStatusAtom)[chatId ?? ""]
    const isAnswering = Boolean(pendingText) || streamingText !== null

    const onSend = async (message: ChatbotOutgoingMessage) => {
        const name = await send(message, chatId, projectId)
        if (name && name !== chatId) navigate(`/chatbot/${name}`, { replace: true })
    }

    const title = chat?.title ?? projects.find((project) => project.name === projectId)?.title

    return (
        <div className="flex min-h-0 flex-1 p-0 md:p-1">
            <Island className="flex-1">
                <ChatbotHeader title={title} chat={chat} />
                {isLoading && !isAnswering
                    ? <div className="flex-1 p-4"><Skeleton className="h-4 w-1/2" /></div>
                    : <ChatbotMessages messages={chat?.messages ?? []} actions={chat?.actions} chatId={chatId} pendingText={pendingText} streamingText={streamingText} status={status} />}
                <div className="shrink-0 p-1.5 md:p-2">
                    <ChatbotComposer key={chatId ?? "new"} onSend={onSend} disabled={isAnswering || (chat ? !chat.can_write : false)} draftKey={`chatbot:${chatId ?? "new"}`} />
                </div>
            </Island>
        </div>
    )
}
