import { useFrappeGetCall } from "frappe-react-sdk"
import { useLocalStorage } from "usehooks-ts"
import { siteKey } from "@lib/site"
import { resolveChoice, withEffort, type ChatbotChoice, type ChatbotModelOption } from "./chatbotChoice"

/** The models the admin allows, and the user's current pick (remembered per browser). */
export const useChatbotChoice = () => {
    const { data } = useFrappeGetCall<{ message: { models: ChatbotModelOption[] } }>(
        "raven.api.chatbot.get_chatbot_options", undefined, undefined, { revalidateOnFocus: false },
    )
    const [stored, setStored] = useLocalStorage<ChatbotChoice | undefined>(siteKey("chatbot-choice"), undefined)
    const options = data?.message.models ?? []
    const choice = resolveChoice(options, stored)

    return {
        options,
        choice,
        pickModel: (model: string) => setStored(resolveChoice(options, { model })),
        pickEffort: (effort: string) => setStored(withEffort(choice, effort)),
    }
}
