import { useEffect, useRef } from "react"
import dayjs from "dayjs"
import { BotMessageSquareIcon, FileBoxIcon } from "lucide-react"
import { Avatar, AvatarFallback, AvatarImage } from "@components/ui/avatar"
import MarkdownRenderer from "@components/ui/markdown"
import { Spinner } from "@components/ui/spinner"
import { useUser } from "@hooks/useUser"
import { useUserCookieData } from "@hooks/useUserCookieData"
import { siteUrl } from "@lib/site"
import _ from "@lib/translate"
import { ChatbotAttachmentCard } from "./ChatbotAttachmentCard"
import type { ChatbotMessage } from "./types"

const AssistantAvatar = () => (
    <Avatar className="size-8 rounded">
        <AvatarFallback className="rounded bg-surface-gray-3 text-ink-gray-7"><BotMessageSquareIcon className="size-4" /></AvatarFallback>
    </Avatar>
)

const Attachments = ({ message }: { message: ChatbotMessage }) => (
    <div className="mt-1 flex flex-wrap gap-2">
        {message.document && (
            <span className="flex items-center gap-1 rounded border border-outline-gray-2 px-2 py-1 text-xs text-ink-gray-7">
                <FileBoxIcon className="size-3" />{message.document.doctype} · {message.document.docname}
            </span>
        )}
        {message.files?.map((file) => <ChatbotAttachmentCard key={file.file_url} file={file} className="h-36 w-36" />)}
    </div>
)

/** A message laid out like a Raven channel message: avatar, then name and time over the body. */
const MessageRow = ({ message }: { message: ChatbotMessage }) => {
    const current = useUserCookieData()
    const author = useUser(message.owner)
    // The optimistic message has no owner yet — it is the current user's.
    const full_name = message.owner && message.owner !== current.name ? author?.full_name || message.owner : current.full_name
    const user_image = message.owner && message.owner !== current.name ? author?.user_image : current.user_image
    const isUser = message.role === "user"
    const time = dayjs(message.creation).format("hh:mm a")

    return (
        <div className="flex items-start gap-3 px-4 py-2">
            {isUser ? (
                <Avatar className="size-8 rounded">
                    <AvatarImage src={user_image ? siteUrl(user_image) : undefined} alt={full_name} />
                    <AvatarFallback className="rounded bg-surface-gray-2 text-xs text-ink-gray-7">{full_name?.charAt(0).toUpperCase()}</AvatarFallback>
                </Avatar>
            ) : <AssistantAvatar />}
            <div className="min-w-0 flex-1">
                <div className="flex items-baseline gap-2">
                    <span className="text-sm font-semibold text-ink-gray-8">{isUser ? full_name : _("Raven AI")}</span>
                    <span className="text-xs text-ink-gray-4">{time}</span>
                </div>
                <div className="text-p-base text-ink-gray-8">
                    {isUser ? <span className="whitespace-pre-wrap">{message.content}</span> : <MarkdownRenderer content={message.content} />}
                </div>
                {isUser && <Attachments message={message} />}
            </div>
        </div>
    )
}

interface ChatbotMessagesProps {
    messages: ChatbotMessage[]
    /** The message just sent, before the server has confirmed it. */
    pendingText: string | null
    /** What the bot has written so far: null when idle, "" while it is still thinking. */
    streamingText: string | null
    /** What the chatbot is doing while it works, e.g. which specialist it is asking. */
    status?: string
}

export const ChatbotMessages = ({ messages, pendingText, streamingText, status }: ChatbotMessagesProps) => {
    const bottomRef = useRef<HTMLDivElement>(null)
    // A block body on purpose: an effect must not return a value (React would call it as the cleanup).
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ block: "end" })
    }, [messages.length, pendingText, streamingText, status])

    return (
        <div className="min-h-0 flex-1 overflow-y-auto py-2">
            {messages.length === 0 && !pendingText && streamingText === null && (
                <p className="px-4 py-2 text-xs text-ink-gray-5">{_("This is the start of your conversation with Raven AI. Ask anything, or type / for skills.")}</p>
            )}
            {messages.map((message, index) => <MessageRow key={index} message={message} />)}
            {pendingText && <MessageRow message={{ role: "user", content: pendingText, creation: new Date().toISOString() }} />}
            {streamingText ? <MessageRow message={{ role: "assistant", content: streamingText, creation: new Date().toISOString() }} /> : null}
            {(pendingText || streamingText !== null) && <div className="flex items-center gap-3 px-4 py-2 pl-[3.75rem] text-p-sm text-ink-gray-5"><Spinner className="size-4" />{status ?? _("Thinking…")}</div>}
            <div ref={bottomRef} />
        </div>
    )
}
