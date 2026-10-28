import { useState, type KeyboardEvent } from "react"
import { MessageCircleQuestionIcon } from "lucide-react"
import { Button } from "@components/ui/button"
import { Input } from "@components/ui/input"
import _ from "@lib/translate"
import { useAnswerChatbotQuestion } from "./useChatbotChat"
import type { ChatbotQuestion } from "./types"

interface ChatbotQuestionCardProps {
    chatId: string
    question: ChatbotQuestion
}

/** A question of the AI: the choices it suggests, and a box for any other answer. Once answered it stays, with the answer. */
export const ChatbotQuestionCard = ({ chatId, question }: ChatbotQuestionCardProps) => {
    const { answer, busy } = useAnswerChatbotQuestion(chatId)
    const [custom, setCustom] = useState("")
    const options: string[] = JSON.parse(question.options)
    const isOpen = question.status === "Pending"

    const submitCustom = () => custom.trim() && answer(question.name, custom.trim())
    const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
        if (event.key !== "Enter" || event.nativeEvent.isComposing) return
        event.preventDefault()
        submitCustom()
    }

    return (
        <div className="mx-4 my-2 ml-[3.75rem] flex max-w-xl flex-col gap-2 rounded-lg border border-outline-gray-2 bg-surface-white p-3">
            <div className="flex items-start gap-2 text-p-base font-medium text-ink-gray-8">
                <MessageCircleQuestionIcon className="mt-0.5 size-4 shrink-0 text-ink-blue-3" />
                <span className="whitespace-pre-line">{question.question}</span>
            </div>
            {isOpen ? (
                <>
                    <div className="flex flex-wrap gap-2">
                        {options.map((option) => (
                            <Button key={option} size="sm" variant="outline" disabled={busy} onClick={() => answer(question.name, option)}>{option}</Button>
                        ))}
                    </div>
                    <div className="flex gap-2">
                        <Input value={custom} disabled={busy} onChange={(event) => setCustom(event.target.value)} onKeyDown={onKeyDown} placeholder={_("Or type your own answer…")} aria-label={_("Your own answer")} />
                        <Button size="sm" disabled={busy || !custom.trim()} onClick={submitCustom}>{_("Send")}</Button>
                    </div>
                </>
            ) : (
                <p className="text-p-sm text-ink-gray-7">{_("You answered:")} <span className="font-medium text-ink-gray-8">{question.answer}</span></p>
            )}
        </div>
    )
}
