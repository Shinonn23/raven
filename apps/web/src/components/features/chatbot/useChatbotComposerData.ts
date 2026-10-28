import { useFrappeGetCall } from "frappe-react-sdk"
import type { ChatbotDocument, ChatbotSkill } from "./types"

export const useChatbotSkills = () => {
    const { data } = useFrappeGetCall<{ message: ChatbotSkill[] }>("raven.api.chatbot.get_skills")
    return data?.message ?? []
}

export type RecommendedDocument = ChatbotDocument & { use_count: number }

/** The documents this user attaches most (server-filtered to ones they can still read). */
export const useRecommendedDocuments = () => {
    const { data } = useFrappeGetCall<{ message: RecommendedDocument[] }>("raven.api.chatbot.get_recommended_documents")
    return data?.message ?? []
}
