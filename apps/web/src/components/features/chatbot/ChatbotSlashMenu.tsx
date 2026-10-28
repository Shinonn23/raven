import { BuildingIcon, UserIcon } from "lucide-react"
import { cn } from "@lib/utils"
import _ from "@lib/translate"
import type { ChatbotSkill } from "./types"

interface ChatbotSlashMenuProps {
    skills: ChatbotSkill[]
    activeIndex: number
    onPick: (skill: ChatbotSkill) => void
}

export const ChatbotSlashMenu = ({ skills, activeIndex, onPick }: ChatbotSlashMenuProps) => (
    <div role="listbox" className="absolute inset-x-0 bottom-full mb-2 max-h-56 overflow-y-auto rounded-lg border border-outline-gray-2 bg-surface-base p-1 shadow-md">
        {skills.length === 0 && <p className="p-3 text-p-sm text-ink-gray-5">{_("No matching skills")}</p>}
        {skills.map((skill, index) => (
            <button
                key={skill.name}
                type="button"
                role="option"
                aria-selected={index === activeIndex}
                onMouseDown={(event) => { event.preventDefault(); onPick(skill) }}
                className={cn("flex w-full items-center gap-2 rounded px-2 py-2 text-start text-sm hover:bg-surface-gray-2", index === activeIndex && "bg-surface-gray-3")}
            >
                {skill.is_company ? <BuildingIcon className="size-4 shrink-0 text-ink-gray-5" /> : <UserIcon className="size-4 shrink-0 text-ink-gray-5" />}
                <span className="text-ink-gray-8">/{skill.command}</span>
                <span className="min-w-0 flex-1 truncate text-ink-gray-5">{skill.title}</span>
            </button>
        ))}
    </div>
)
