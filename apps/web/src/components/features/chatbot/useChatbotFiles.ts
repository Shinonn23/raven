import { useState } from "react"
import { useFrappeFileUpload } from "frappe-react-sdk"
import { errorResponseToast } from "@components/ui/error-banner"
import _ from "@lib/translate"
import type { SystemFile } from "../attach-picker/types"
import type { ChatbotAttachment } from "./types"

/** The files staged on the chatbot draft: uploaded from the computer or picked from the system. */
export const useChatbotFiles = () => {
    const [files, setFiles] = useState<ChatbotAttachment[]>([])
    const { upload } = useFrappeFileUpload()

    const add = (added: ChatbotAttachment[]) => setFiles((previous) => [...previous, ...added])

    const addUploads = async (picked: File[]) => {
        try {
            const uploaded = await Promise.all(picked.map((file) => upload(file, { isPrivate: true })))
            add(uploaded.map(({ file_url, file_name }) => ({ file_url, file_name })))
        } catch (error) {
            errorResponseToast(_("Could not upload the file"), error as never)
        }
    }

    const addSystemFiles = (picked: SystemFile[]) => add(picked.map(({ file_url, file_name }) => ({ file_url, file_name })))

    return { files, addUploads, addSystemFiles, remove: (file: ChatbotAttachment) => setFiles((previous) => previous.filter((other) => other !== file)), clear: () => setFiles([]) }
}
