import { atom, useSetAtom } from "jotai"
import { useFrappeEventListener, useSWRConfig } from "frappe-react-sdk"
import { errorResponseToast } from "@components/ui/error-banner"
import _ from "@lib/translate"
import { useChatbot } from "./useChatbot"
import { chatKey } from "./useChatbotChat"

/** Text the bot has written so far, per chat. A chat is "answering" while it has an entry ("" = still thinking). */
export const chatbotStreamsAtom = atom<Record<string, string>>({})

/** What the chatbot is doing right now per chat, e.g. "Asking Accounting Helper…". Cleared when the answer is done. */
export const chatbotStatusAtom = atom<Record<string, string>>({})

const without = (streams: Record<string, string>, chat: string) => {
    const { [chat]: _finished, ...rest } = streams
    return rest
}

/** Listens for the bot's streamed answers. Mount once, above every chatbot page, so a stream survives navigation. */
export const useChatbotStream = () => {
    const setStreams = useSetAtom(chatbotStreamsAtom)
    const setStatuses = useSetAtom(chatbotStatusAtom)
    const { mutate } = useSWRConfig()
    const { refresh } = useChatbot()

    useFrappeEventListener("chatbot_delta", ({ chat, text }: { chat: string; text: string }) =>
        setStreams((streams) => ({ ...streams, [chat]: (streams[chat] ?? "") + text })))

    useFrappeEventListener("chatbot_status", ({ chat, text }: { chat: string; text: string }) =>
        setStatuses((statuses) => ({ ...statuses, [chat]: text })))

    useFrappeEventListener("chatbot_title", ({ chat }: { chat: string }) => {
        mutate(chatKey(chat))
        refresh()
    })

    useFrappeEventListener("chatbot_done", async ({ chat, failed }: { chat: string; failed: boolean }) => {
        // Swap the streamed text for the saved message first, so the answer never blinks out.
        await Promise.all([mutate(chatKey(chat)), refresh()])
        setStreams((streams) => without(streams, chat))
        setStatuses((statuses) => without(statuses, chat))
        if (failed) errorResponseToast(_("The chatbot could not answer"))
    })
}
