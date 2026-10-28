import { useFrappeGetCall } from "frappe-react-sdk"
import type { SystemFile } from "./types"

/** Files in the system the current user may read, newest first, filtered server-side by `search`. */
export const useAttachableFiles = (search: string, enabled: boolean) => {
    const { data, isLoading } = useFrappeGetCall<{ message: SystemFile[] }>(
        "raven.api.upload_file.get_attachable_files",
        { search },
        enabled ? ["attachable-files", search] : null,
        { keepPreviousData: true },
    )
    return { files: data?.message ?? [], isLoading }
}
