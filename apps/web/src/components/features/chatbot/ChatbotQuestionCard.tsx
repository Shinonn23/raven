import { useState } from "react"
import { Button } from "@components/ui/button"
import _ from "@lib/translate"
import { ChatbotQuestionItem, QuestionHeading } from "./ChatbotQuestionItem"
import { allAnswers, emptyDraft, isComplete, type AskedQuestion, type Draft } from "./questionAnswers"
import { useAnswerChatbotQuestion } from "./useChatbotChat"
import type { ChatbotQuestion } from "./types"

interface ChatbotQuestionCardProps {
    chatId: string
    question: ChatbotQuestion
}

/** The questions of the AI as one card: choices (one or several) and a box for any other answer for each; all answers are sent together. */
export const ChatbotQuestionCard = ({ chatId, question }: ChatbotQuestionCardProps) => {
    const { answer, busy } = useAnswerChatbotQuestion(chatId)
    const asked: AskedQuestion[] = JSON.parse(question.questions)
    const [drafts, setDrafts] = useState<Draft[]>(() => asked.map(() => emptyDraft))
    const isOpen = question.status === "Pending"
    const answered: string[] = question.answers ? JSON.parse(question.answers) : []
    const update = (index: number, change: (draft: Draft) => Draft) => setDrafts((previous) => previous.map((draft, other) => (other === index ? change(draft) : draft)))

    return (
        <div className="mx-4 my-2 ml-[3.75rem] flex max-w-xl flex-col gap-4 rounded-lg border border-outline-gray-2 bg-surface-white p-3">
            {asked.map((item, index) => (
                <div key={item.question} className="flex flex-col gap-2">
                    <QuestionHeading text={item.question} />
                    {isOpen
                        ? <ChatbotQuestionItem item={item} draft={drafts[index]} busy={busy} onChange={(change) => update(index, change)} />
                        : <p className="pl-6 text-p-sm text-ink-gray-7">{_("You answered:")} <span className="font-medium text-ink-gray-8">{answered[index]}</span></p>}
                </div>
            ))}
            {isOpen && (
                <div className="flex items-center gap-2">
                    <Button size="sm" disabled={busy || !isComplete(asked, drafts)} onClick={() => answer(question.name, allAnswers(asked, drafts))}>{_("Submit")}</Button>
                    {!isComplete(asked, drafts) && <span className="text-xs text-ink-gray-5">{_("Answer every question to send.")}</span>}
                </div>
            )}
        </div>
    )
}
