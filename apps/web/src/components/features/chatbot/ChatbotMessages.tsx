import { Fragment, useEffect, useRef } from "react"
import dayjs from "dayjs"
import { BotMessageSquareIcon } from "lucide-react"
import { Avatar, AvatarFallback, AvatarImage } from "@components/ui/avatar"
import MarkdownRenderer from "@components/ui/markdown"
import { Spinner } from "@components/ui/spinner"
import { useUser } from "@hooks/useUser"
import { useUserCookieData } from "@hooks/useUserCookieData"
import { siteUrl } from "@lib/site"
import { cn } from "@lib/utils"
import _ from "@lib/translate"
import { DocumentLinkRenderer } from "@components/features/message/renderers/DocumentLinkRenderer"
import { ChatbotActionCard } from "./ChatbotActionCard"
import { ChatbotAttachmentCard } from "./ChatbotAttachmentCard"
import { useManualImageOrigins } from "./useChatbotChoice"
import type { ChatbotAction, ChatbotMessage } from "./types"

const AssistantAvatar = () => (
    <Avatar className="size-8 rounded">
        <AvatarFallback className="rounded bg-surface-gray-3 text-ink-gray-7"><BotMessageSquareIcon className="size-4" /></AvatarFallback>
    </Avatar>
)

/** An attached system document is the same card as in a channel: its main fields, and a click opens it. */
const Attachments = ({ message, alignRight }: { message: ChatbotMessage; alignRight?: boolean }) => (
    <div className={cn("mt-1 flex flex-wrap gap-2", alignRight && "justify-end")}>
        {message.document && <DocumentLinkRenderer doctype={message.document.doctype} docname={message.document.docname} className="w-96 max-w-full" />}
        {message.files?.map((file) => <ChatbotAttachmentCard key={file.file_url} file={file} className="h-36 w-36" />)}
    </div>
)

const Bubble = ({ children }: { children: React.ReactNode }) => (
    <div className="w-fit max-w-full whitespace-pre-wrap rounded-2xl bg-surface-gray-2 px-3.5 py-2 text-p-base text-ink-gray-8">{children}</div>
)

/** The current user's own message: on the right, in a bubble, as in any chat app. */
const OwnMessage = ({ message }: { message: ChatbotMessage }) => (
    <div className="flex flex-col items-end gap-0.5 px-4 py-2">
        <span className="text-xs text-ink-gray-4">{dayjs(message.creation).format("hh:mm a")}</span>
        <div className="flex max-w-[88%] flex-col items-end md:max-w-[70%]">
            {message.content && <Bubble>{message.content}</Bubble>}
            <Attachments message={message} alignRight />
        </div>
    </div>
)

/** Another person's message in a chat shared with the user: on the left, with who wrote it. */
const OtherPersonMessage = ({ message }: { message: ChatbotMessage }) => {
    const author = useUser(message.owner)
    const name = author?.full_name || message.owner
    return (
        <div className="flex items-start gap-3 px-4 py-2">
            <Avatar className="size-8 rounded">
                <AvatarImage src={author?.user_image ? siteUrl(author.user_image) : undefined} alt={name} />
                <AvatarFallback className="rounded bg-surface-gray-2 text-xs text-ink-gray-7">{name?.charAt(0).toUpperCase()}</AvatarFallback>
            </Avatar>
            <div className="flex min-w-0 max-w-[88%] flex-col md:max-w-[70%]">
                <div className="flex items-baseline gap-2">
                    <span className="text-sm font-semibold text-ink-gray-8">{name}</span>
                    <span className="text-xs text-ink-gray-4">{dayjs(message.creation).format("hh:mm a")}</span>
                </div>
                {message.content && <Bubble>{message.content}</Bubble>}
                <Attachments message={message} />
            </div>
        </div>
    )
}

/** The assistant's answer: on the left, Raven channel style (avatar, name, time) with the answer as formatted text. */
const AssistantMessage = ({ message }: { message: ChatbotMessage }) => {
    const imageOrigins = useManualImageOrigins()
    return (
        <div className="flex items-start gap-3 px-4 py-2">
            <AssistantAvatar />
            <div className="min-w-0 flex-1">
                <div className="flex items-baseline gap-2">
                    <span className="text-sm font-semibold text-ink-gray-8">{_("Raven AI")}</span>
                    <span className="text-xs text-ink-gray-4">{dayjs(message.creation).format("hh:mm a")}</span>
                </div>
                <div className="text-p-base text-ink-gray-8">
                    <MarkdownRenderer content={message.content} className="tiptap chatbot-markdown" allowHtml={false} imageOrigins={imageOrigins} />
                </div>
            </div>
        </div>
    )
}

const MessageRow = ({ message }: { message: ChatbotMessage }) => {
    const currentUser = useUserCookieData().name
    if (message.role === "assistant") return <AssistantMessage message={message} />
    // The message just sent has no owner yet: it is the current user's.
    const isMine = !message.owner || message.owner === currentUser
    return isMine ? <OwnMessage message={message} /> : <OtherPersonMessage message={message} />
}

/** A card belongs under the answer that followed the messages the chat had when it was asked; a position past the last message
 *  (the answer is still being written) puts it at the end. */
const cardPosition = (action: ChatbotAction, messages: ChatbotMessage[]) => Math.min(action.message_position, messages.length)

const cardsAfter = (index: number, messages: ChatbotMessage[], actions: ChatbotAction[]) =>
    actions.filter((action) => cardPosition(action, messages) === index)

interface ChatbotMessagesProps {
    messages: ChatbotMessage[]
    /** Changes the AI asked to make, waiting for the user's answer or already answered. */
    actions?: ChatbotAction[]
    chatId?: string
    /** The message just sent, before the server has confirmed it. */
    pendingText: string | null
    /** What the bot has written so far: null when idle, "" while it is still thinking. */
    streamingText: string | null
    /** What the chatbot is doing while it works, e.g. which specialist it is asking. */
    status?: string
}

export const ChatbotMessages = ({ messages, actions = [], chatId, pendingText, streamingText, status }: ChatbotMessagesProps) => {
    const bottomRef = useRef<HTMLDivElement>(null)
    // A block body on purpose: an effect must not return a value (React would call it as the cleanup).
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ block: "end" })
    }, [messages.length, actions.length, pendingText, streamingText, status])

    return (
        <div className="min-h-0 flex-1 overflow-y-auto py-2">
            {messages.length === 0 && !pendingText && streamingText === null && (
                <p className="px-4 py-2 text-xs text-ink-gray-5">{_("This is the start of your conversation with Raven AI. Ask anything, or type / for skills.")}</p>
            )}
            {messages.map((message, index) => (
                <Fragment key={index}>
                    <MessageRow message={message} />
                    {chatId && cardsAfter(index, messages, actions).map((action) => <ChatbotActionCard key={action.name} chatId={chatId} action={action} />)}
                </Fragment>
            ))}
            {chatId && cardsAfter(messages.length, messages, actions).map((action) => <ChatbotActionCard key={action.name} chatId={chatId} action={action} />)}
            {pendingText && <MessageRow message={{ role: "user", content: pendingText, creation: new Date().toISOString() }} />}
            {streamingText ? <MessageRow message={{ role: "assistant", content: streamingText, creation: new Date().toISOString() }} /> : null}
            {(pendingText || streamingText !== null) && <div className="flex items-center gap-3 px-4 py-2 pl-[3.75rem] text-p-sm text-ink-gray-5"><Spinner className="size-4" />{status ?? _("Thinking…")}</div>}
            <div ref={bottomRef} />
        </div>
    )
}
