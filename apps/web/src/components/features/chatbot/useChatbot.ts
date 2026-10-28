import { useFrappeCreateDoc, useFrappeDeleteDoc, useFrappeGetCall, useFrappeUpdateDoc } from "frappe-react-sdk"
import type { ChatbotChatSummary, ChatbotProject } from "./types"

type Overview = { projects: ChatbotProject[]; chats: ChatbotChatSummary[] }

/** The current user's chatbot projects and chats, plus the document mutations the sidebar needs. */
export const useChatbot = () => {
    const { data, isLoading, mutate: refresh } = useFrappeGetCall<{ message: Overview }>("raven.api.chatbot.get_chatbot_overview")
    const { createDoc } = useFrappeCreateDoc()
    const { updateDoc } = useFrappeUpdateDoc()
    const { deleteDoc } = useFrappeDeleteDoc()

    const createProject = async (title: string): Promise<ChatbotProject> => {
        const project = await createDoc("Raven Chatbot Project", { title })
        await refresh()
        return project
    }
    const renameChat = (name: string, title: string) => updateDoc("Raven Chatbot Chat", name, { title }).then(() => refresh())
    const deleteChat = (name: string) => deleteDoc("Raven Chatbot Chat", name).then(() => refresh())

    return {
        projects: data?.message.projects ?? [],
        chats: data?.message.chats ?? [],
        isLoading,
        refresh,
        createProject,
        renameChat,
        deleteChat,
    }
}
