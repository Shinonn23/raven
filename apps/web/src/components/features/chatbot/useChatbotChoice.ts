import { useFrappeGetCall } from "frappe-react-sdk"
import { useLocalStorage } from "usehooks-ts"
import { siteKey } from "@lib/site"
import { resolveChoice, withEffort, type ChatbotChoice, type ChatbotModelOption } from "./chatbotChoice"

type ChatbotOptions = { models: ChatbotModelOption[]; manual_origins: string[] }

const useChatbotOptions = () => {
    const { data } = useFrappeGetCall<{ message: ChatbotOptions }>(
        "raven.api.chatbot.get_chatbot_options", undefined, undefined, { revalidateOnFocus: false },
    )
    return data?.message
}

/** The manual sites whose pictures an answer may show. Pictures from anywhere else are not loaded. */
export const useManualImageOrigins = () => useChatbotOptions()?.manual_origins ?? []

/** The models the admin allows, and the user's current pick (remembered per browser). */
export const useChatbotChoice = () => {
    const options = useChatbotOptions()
    const [stored, setStored] = useLocalStorage<ChatbotChoice | undefined>(siteKey("chatbot-choice"), undefined)
    const models = options?.models ?? []
    const choice = resolveChoice(models, stored)

    return {
        options: models,
        choice,
        pickModel: (model: string) => setStored(resolveChoice(models, { model })),
        pickEffort: (effort: string) => setStored(withEffort(choice, effort)),
    }
}
