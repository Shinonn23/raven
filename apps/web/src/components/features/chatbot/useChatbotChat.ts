import { useState } from "react"
import { useSetAtom } from "jotai"
import { useFrappeGetCall, useFrappePostCall, useSWRConfig } from "frappe-react-sdk"
import _ from "@lib/translate"
import { errorResponseToast } from "@components/ui/error-banner"
import { useChatbot } from "./useChatbot"
import { useChatbotChoice } from "./useChatbotChoice"
import { chatbotStreamsAtom } from "./useChatbotStream"
import type { ChatbotChat, ChatbotOutgoingMessage, ChatbotShare } from "./types"

export const chatKey = (chatId: string) => ["chatbot-chat", chatId]

/** Messages of one chat; pass `undefined` for a chat that does not exist yet. */
export const useChatbotChat = (chatId?: string) => {
    const { data, isLoading } = useFrappeGetCall<{ message: ChatbotChat }>(
        "raven.api.chatbot.get_chat",
        { chat: chatId },
        chatId ? chatKey(chatId) : null,
    )
    return { chat: data?.message, isLoading }
}

/** Sends a message (creating the chat when `chatId` is absent) and resolves with the chat id. */
export const useSendChatbotMessage = () => {
    const { call } = useFrappePostCall<{ message: ChatbotChat }>("raven.api.chatbot.send_message")
    const { mutate } = useSWRConfig()
    const { refresh } = useChatbot()
    const setStreams = useSetAtom(chatbotStreamsAtom)
    const [pendingText, setPendingText] = useState<string | null>(null)

    const send = async ({ text, files, document, model, effort }: ChatbotOutgoingMessage, chatId?: string, projectId?: string | null) => {
        setPendingText(text)
        try {
            const { message: chat } = await call({ text, chat: chatId, project: projectId, files, document, model, effort })
            // The question is saved; the answer arrives over realtime (see useChatbotStream).
            setStreams((streams) => ({ ...streams, [chat.name]: "" }))
            await mutate(chatKey(chat.name), { message: chat }, { revalidate: false })
            await refresh()
            return chat.name
        } catch (error) {
            errorResponseToast(_("The chatbot could not answer"), error as never)
            return undefined
        } finally {
            setPendingText(null)
        }
    }

    return { send, pendingText }
}

/** Who a chat is shared with, plus the owner-only actions to change that. */
export const useChatbotShares = (chatId: string, enabled: boolean) => {
    const { data, mutate } = useFrappeGetCall<{ message: ChatbotShare[] }>(
        "raven.api.chatbot.get_chat_shares", { chat: chatId }, enabled ? ["chatbot-shares", chatId] : null,
    )
    const { call: share } = useFrappePostCall<{ message: ChatbotShare[] }>("raven.api.chatbot.share_chat")
    const { call: unshare } = useFrappePostCall<{ message: ChatbotShare[] }>("raven.api.chatbot.unshare_chat")

    return {
        shares: data?.message ?? [],
        share: (user: string, canWrite: boolean) => share({ chat: chatId, user, can_write: canWrite }).then((result) => mutate(result, { revalidate: false })),
        unshare: (user: string) => unshare({ chat: chatId, user }).then((result) => mutate(result, { revalidate: false })),
    }
}

/** Approve or reject a card the AI asked for. The chat is reloaded so the card shows its outcome; until then the buttons stay off. */
export const useDecideChatbotAction = (chatId: string) => {
    const { call } = useFrappePostCall<{ message: { status: string; result: string | null } }>("raven.api.chatbot.decide_action")
    const { mutate } = useSWRConfig()
    const [busy, setBusy] = useState(false)

    const decide = async (action: string, approve: boolean) => {
        setBusy(true)
        try {
            await call({ action, approve })
        } catch (error) {
            errorResponseToast(_("Could not record your answer"), error as never)
        }
        await mutate(chatKey(chatId))
        setBusy(false)
    }

    return { decide, busy }
}

/** Send the answers to a set of questions of the AI. They become the user's next message and the AI carries on. */
export const useAnswerChatbotQuestion = (chatId: string) => {
    const { call } = useFrappePostCall<{ message: ChatbotChat }>("raven.api.chatbot.answer_question")
    const { mutate } = useSWRConfig()
    const { refresh } = useChatbot()
    const { choice } = useChatbotChoice()
    const setStreams = useSetAtom(chatbotStreamsAtom)
    const [busy, setBusy] = useState(false)

    const answer = async (question: string, answers: string[]) => {
        setBusy(true)
        try {
            const { message: chat } = await call({ question, answers, model: choice?.model, effort: choice?.effort })
            setStreams((streams) => ({ ...streams, [chatId]: "" }))
            await mutate(chatKey(chatId), { message: chat }, { revalidate: false })
            await refresh()
        } catch (error) {
            errorResponseToast(_("Could not send your answer"), error as never)
            await mutate(chatKey(chatId))
        }
        setBusy(false)
    }

    return { answer, busy }
}
