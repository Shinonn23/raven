import { useState } from "react"
import { NavLink, useNavigate } from "react-router-dom"
import { FolderIcon, PlusIcon, SquarePenIcon } from "lucide-react"
import { Button } from "@components/ui/button"
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@components/ui/empty"
import { Skeleton } from "@components/ui/skeleton"
import _ from "@lib/translate"
import { ChatbotChatRow } from "./ChatbotChatRow"
import { ChatbotNameDialog } from "./ChatbotNameDialog"
import { useUserCookieData } from "@hooks/useUserCookieData"
import { useChatbot } from "./useChatbot"

const SectionHeader = ({ title, action }: { title: string; action?: React.ReactNode }) => (
    <div className="flex items-center justify-between px-4 pb-1 pt-3 text-xs text-ink-gray-5">
        <span>{title}</span>
        {action}
    </div>
)

const ProjectSection = () => {
    const { projects, chats, createProject } = useChatbot()
    const navigate = useNavigate()
    const [isCreating, setIsCreating] = useState(false)

    const create = async (title: string) => {
        const project = await createProject(title)
        navigate(`/chatbot/new?project=${project.name}`)
    }

    return (
        <>
            <SectionHeader title={_("Projects")} action={
                <Button variant="ghost" size="xs" isIconButton aria-label={_("Create project")} onClick={() => setIsCreating(true)}>
                    <PlusIcon className="size-3.5" />
                </Button>
            } />
            {projects.map((project) => (
                <div key={project.name}>
                    <NavLink to={`/chatbot/new?project=${project.name}`} className="block px-2 py-0.5">
                        <div className="flex items-center gap-2 rounded px-2 py-2 text-sm text-ink-gray-8 hover:bg-surface-gray-3">
                            <FolderIcon className="size-4 shrink-0 text-ink-gray-5" />
                            <span className="truncate">{project.title}</span>
                        </div>
                    </NavLink>
                    {chats.filter((chat) => chat.project === project.name).map((chat) => <ChatbotChatRow key={chat.name} chat={chat} indented />)}
                </div>
            ))}
            <ChatbotNameDialog
                open={isCreating}
                onOpenChange={setIsCreating}
                title={_("Create project")}
                label={_("Project name")}
                submitLabel={_("Create project")}
                placeholder={_("Copenhagen Trip")}
                hint={_("Projects keep chats in one place. Use them for ongoing work, or just to keep things tidy.")}
                onSubmit={create}
            />
        </>
    )
}

/** Permanent chatbot rail: same frame as the Direct Messages sidebar. */
export const ChatbotSidebar = () => {
    const { chats, isLoading } = useChatbot()
    const { name: currentUser } = useUserCookieData()
    const looseChats = chats.filter((chat) => !chat.project && chat.owner === currentUser)
    const sharedChats = chats.filter((chat) => chat.owner !== currentUser)

    return (
        <nav className="flex h-full w-full flex-col bg-surface-base md:bg-surface-sidebar">
            <div className="flex h-11 shrink-0 items-center justify-between gap-1 border-b px-2 py-2 md:h-auto md:border-b-0">
                <span className="px-1 py-1 text-xl font-medium text-ink-gray-8 md:text-base">{_("Chatbot")}</span>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden pb-2">
                <NavLink to="/chatbot/new" className="block px-2 py-0.5">
                    <div className="flex items-center gap-2 rounded px-2 py-2 text-sm text-ink-gray-8 hover:bg-surface-gray-3">
                        <SquarePenIcon className="size-4 shrink-0" />{_("New chat")}
                    </div>
                </NavLink>
                <ProjectSection />
                <SectionHeader title={_("Chats")} />
                {isLoading && <div className="px-4 py-2"><Skeleton className="h-3 w-3/4" /></div>}
                {looseChats.map((chat) => <ChatbotChatRow key={chat.name} chat={chat} />)}
                {sharedChats.length > 0 && <SectionHeader title={_("Shared with me")} />}
                {sharedChats.map((chat) => <ChatbotChatRow key={chat.name} chat={chat} />)}
                {!isLoading && chats.length === 0 && (
                    <Empty>
                        <EmptyMedia><SquarePenIcon /></EmptyMedia>
                        <EmptyHeader>
                            <EmptyTitle>{_("No chats yet")}</EmptyTitle>
                            <EmptyDescription>{_("Ask the chatbot something to get started.")}</EmptyDescription>
                        </EmptyHeader>
                    </Empty>
                )}
            </div>
        </nav>
    )
}
