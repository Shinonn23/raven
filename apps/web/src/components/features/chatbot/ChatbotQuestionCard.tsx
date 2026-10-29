import { useState } from "react"
import { CheckIcon, ChevronDownIcon, ChevronRightIcon, CircleCheckIcon, CircleSlashIcon } from "lucide-react"
import { Badge } from "@components/ui/badge"
import { Button } from "@components/ui/button"
import _ from "@lib/translate"
import { ChatbotQuestionItem, QuestionHeading } from "./ChatbotQuestionItem"
import { allAnswers, emptyDraft, hasAnyAnswer, nextToAnswer, type AskedQuestion, type Draft } from "./questionAnswers"
import { useAnswerChatbotQuestion } from "./useChatbotChat"
import type { ChatbotQuestion } from "./types"

const CARD = "mx-4 my-2 ml-[3.75rem] max-w-xl rounded-lg border border-outline-gray-2 bg-surface-white"
/** From this many questions on, they are asked one at a time with a summary of the others. */
const STEPPER_FROM = 3

interface ChatbotQuestionCardProps {
    chatId: string
    question: ChatbotQuestion
}

/** The AI's questions as one card. While open it is a shortcut (answer here, or just type in the chat); once answered or skipped it shrinks to a line. */
export const ChatbotQuestionCard = ({ chatId, question }: ChatbotQuestionCardProps) => {
    const asked: AskedQuestion[] = JSON.parse(question.questions)
    return question.status === "Pending" ? <OpenQuestions chatId={chatId} question={question} asked={asked} /> : <ClosedQuestions question={question} asked={asked} />
}

const OpenQuestions = ({ chatId, question, asked }: ChatbotQuestionCardProps & { asked: AskedQuestion[] }) => {
    const { answer, busy } = useAnswerChatbotQuestion(chatId)
    const [drafts, setDrafts] = useState<Draft[]>(() => asked.map(() => emptyDraft))
    const [current, setCurrent] = useState(0)
    const stepper = asked.length >= STEPPER_FROM
    const answers = allAnswers(asked, drafts)
    const update = (index: number, change: (draft: Draft) => Draft) => setDrafts((previous) => previous.map((draft, other) => (other === index ? change(draft) : draft)))
    const goNext = (index: number) => setCurrent(nextToAnswer(asked, drafts, index))

    return (
        <div className={`${CARD} flex flex-col gap-3 p-3`}>
            {asked.map((item, index) => (stepper && index !== current ? (
                <button key={item.question} type="button" onClick={() => setCurrent(index)}
                    className="flex items-center gap-2 rounded-md border border-outline-gray-2 px-2.5 py-1.5 text-left text-p-sm hover:bg-surface-gray-1">
                    {answers[index] ? <CheckIcon className="size-4 shrink-0 text-ink-green-8" /> : <span className="size-4 shrink-0" />}
                    <span className="min-w-0 flex-1 truncate text-ink-gray-7">{item.question}</span>
                    <span className="max-w-[40%] truncate font-medium text-ink-gray-8">{answers[index]}</span>
                    <span className="shrink-0 text-xs text-ink-gray-4">{index + 1}/{asked.length}</span>
                </button>
            ) : (
                <div key={item.question} className="flex flex-col gap-2">
                    <QuestionHeading text={item.question} step={stepper ? `${index + 1}/${asked.length}` : undefined} />
                    <ChatbotQuestionItem item={item} draft={drafts[index]} busy={busy} onChange={(change) => update(index, change)} onPicked={stepper ? () => goNext(index) : undefined} />
                    {stepper && index < asked.length - 1 && <Button size="sm" variant="ghost" className="w-fit" onClick={() => goNext(index)}>{_("Next")}</Button>}
                </div>
            )))}
            <div className="flex items-center gap-2">
                <Button size="sm" disabled={busy || !hasAnyAnswer(asked, drafts)} onClick={() => answer(question.name, answers)}>{_("Submit")}</Button>
                <span className="text-xs text-ink-gray-5">{_("Or just type your answer in the chat.")}</span>
            </div>
        </div>
    )
}

const ClosedQuestions = ({ question, asked }: { question: ChatbotQuestion; asked: AskedQuestion[] }) => {
    const [open, setOpen] = useState(false)
    const answered = question.status === "Answered"
    const answers: string[] = question.answers ? JSON.parse(question.answers) : []
    return (
        <div className={`${CARD} overflow-hidden`}>
            <button type="button" aria-expanded={open} onClick={() => setOpen((value) => !value)} className="flex w-full items-center gap-2 px-3 py-2 text-left text-p-sm hover:bg-surface-gray-1">
                {answered ? <CircleCheckIcon className="size-4 shrink-0 text-ink-green-8" /> : <CircleSlashIcon className="size-4 shrink-0 text-ink-gray-5" />}
                <span className="min-w-0 flex-1 truncate text-ink-gray-7">{asked[0]?.question}{asked.length > 1 ? ` (+${asked.length - 1})` : ""}</span>
                <Badge variant="subtle" theme={answered ? "green" : "gray"}>{answered ? _("Answered") : _("Skipped")}</Badge>
                {open ? <ChevronDownIcon className="size-4 shrink-0" /> : <ChevronRightIcon className="size-4 shrink-0" />}
            </button>
            {open && (
                <div className="flex flex-col gap-2 border-t border-outline-gray-2 p-3">
                    {asked.map((item, index) => (
                        <div key={item.question} className="flex flex-col gap-0.5 text-p-sm">
                            <span className="text-ink-gray-5">{item.question}</span>
                            <span className="font-medium text-ink-gray-8">{answers[index] || (answered ? _("(not answered)") : "—")}</span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
