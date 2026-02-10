import {getOlvidRuntime} from "./runtime";
import {ResolvedOlvidAccount, resolveOlvidAccount} from "./accounts";
import {CoreConfig} from "./types";
import {datatypes, OlvidClient} from "@olvid/bot-node";
import { Type } from "@sinclair/typebox";

function getOlvidClient(olvidChannelAccountId?: string): OlvidClient {
    const runtime = getOlvidRuntime();
    const config = runtime.config.loadConfig();

    // Retrieve the configuration/credentials for the specific olvidChannelAccountId, or fallback to default
    let olvidAccount: ResolvedOlvidAccount = resolveOlvidAccount({cfg: config as CoreConfig, accountId: olvidChannelAccountId ?? "default"});
    if (!olvidAccount || !olvidAccount.daemonUrl || !olvidAccount.clientKey) {
        olvidAccount = resolveOlvidAccount({cfg: config as CoreConfig, accountId: "default"});
    }
    return new OlvidClient({clientKey: olvidAccount.clientKey, serverUrl: olvidAccount.daemonUrl});
}

export const olvidAgentTools = [
    {
        name: "olvid_list_discussions",
        label: "Olvid List Discussions",
        description: "Shows a list of every discussion (private or group) that belongs to **your** Olvid profile, including IDs, titles, and participant details.",
        parameters: Type.Object({
            olvidChannelAccountId: Type.Optional(Type.String())
        }),
        async execute(_id: string, params: unknown) {
            const client = getOlvidClient((params as {olvidChannelAccountId: string}).olvidChannelAccountId);
            const result: { content: any, details: string; } = {
                content: [],
                details: "List of my discussions in Olvid."
            };
            for await (const discussion of client.discussionList()) {
                result.content.push({type: "text", text: JSON.stringify(discussion.toJson())});
            }
            client.stop();
            return result;
        }
    },
    {
        name: "olvid_list_contacts",
        label: "Olvid List Contacts",
        description: "Returns the full contact list for **your** Olvid profile, with each contact’s ID, name and status.",
        parameters: Type.Object({
            olvidChannelAccountId: Type.Optional(Type.String())
        }),
        async execute(_id: string, params: unknown) {
            const client = getOlvidClient((params as {olvidChannelAccountId: string}).olvidChannelAccountId);
            const result: { content: any, details: string; } = {
                content: [],
                details: "Olvid contacts list."
            };
            for await (const contact of client.contactList()) {
                result.content.push({type: "text", text: JSON.stringify(contact.toJson())});
            }
            client.stop();
            return result;
        }
    },
    {
        name: "olvid_list_groups",
        label: "Olvid List Groups",
        description: "Lists every Olvid groups that **you** are a member of, including group IDs, names, and member lists.",
        parameters: Type.Object({
            olvidChannelAccountId: Type.Optional(Type.String())
        }),
        async execute(_id: string, params: unknown) {
            const client = getOlvidClient((params as {olvidChannelAccountId: string}).olvidChannelAccountId);
            const result: { content: any, details: string; } = {
                content: [],
                details: "List of my Olvid groups"
            };
            for await (const contact of client.groupList()) {
                result.content.push({type: "text", text: JSON.stringify(contact.toJson())});
            }
            client.stop();
            return result;
        }
    },
    {
        name: "olvid_start_call",
        label: "Olvid Start Call",
        description: "Initiates a voice/video call inside any discussion that **belongs to you** (private or group). Returns the call ID.",
        parameters: Type.Object({
            olvidChannelAccountId: Type.Optional(Type.String()),
            discussionId: Type.Number()
        }),
        async execute(_id: string, params: unknown) {
            const client = getOlvidClient((params as {olvidChannelAccountId: string}).olvidChannelAccountId);
            const discussionId: number = (params as {discussionId: number}).discussionId;
            let callId = await client.callStartDiscussionCall({discussionId: BigInt(discussionId)});
            const result: { content: any, details: string; } = {
                content: [{type: "text", text: callId}],
                details: "Call identifier."
            };
            client.stop();
            return result;
        }
    },
    {
        name: "olvid_group_add_member",
        label: "Olvid Group Add Member",
        description: "Adds a contact (by ID) to an Olvid group **you’re an admin of**, therefore giving you control over group membership.",
        parameters: Type.Object({olvidChannelAccountId: Type.Optional(Type.String()), groupId: Type.Number(), contactIdToAdd: Type.Number(), filePath: Type.String()}),
        async execute(_id: string, params: unknown) {
            const client = getOlvidClient((params as {olvidChannelAccountId: string}).olvidChannelAccountId);
            const groupId: number = (params as {groupId: number}).groupId;
            const contactIdToAdd: number = (params as {contactIdToAdd: number}).contactIdToAdd;
            const group = await client.groupGet({groupId: BigInt(groupId)});
            group.members.push(new datatypes.GroupMember({contactId: BigInt(contactIdToAdd)}));
            const ret = await client.groupUpdate({group: group});
            const result: { content: any, details: string; } = {
                content: [{type: "text", text: JSON.stringify(ret)}],
                details: "Result of GroupAddMember method."
            };
            client.stop();
            return result;
        }
    },
    {
        name: "olvid_group_kick_member",
        label: "Olvid Group Kick Member",
        description: "Removes a contact from an Olvid group you admin.",
        parameters: Type.Object({olvidChannelAccountId: Type.Optional(Type.String()), groupId: Type.Number(), contactIdToKick: Type.Number(), filePath: Type.String()}),
        async execute(_id: string, params: unknown) {
            const client = getOlvidClient((params as {olvidChannelAccountId: string}).olvidChannelAccountId);
            const groupId: number = (params as {groupId: number}).groupId;
            const contactIdToKick: number = (params as {contactIdToKick: number}).contactIdToKick;
            const group = await client.groupGet({groupId: BigInt(groupId)});
            group.members = group.members.filter(m => m.contactId !== BigInt(contactIdToKick));
            const ret = await client.groupUpdate({group: group});
            const result: { content: any, details: string; } = {
                content: [{type: "text", text: JSON.stringify(ret)}],
                details: "Result of GroupKickMember method."
            };
            client.stop();
            return result;
        }
    },
    {
        name: "olvid_create_group",
        label: "Olvid Create Group",
        description: "Creates a new Olvid group under **your** Olvid profile. Specify the group name and the IDs of the initial members.",
        parameters: Type.Object({
            olvidChannelAccountId: Type.Optional(Type.String()),
            groupName: Type.String(),
            contactIds: Type.Array(Type.Number())
        }),
        async execute(_id: string, params: unknown) {
            const client = getOlvidClient((params as {olvidChannelAccountId: string}).olvidChannelAccountId);
            const groupName: string = (params as {groupName: string}).groupName;
            const contactIds: number[] = (params as {contactIds: number[]}).contactIds;
            let group = await client.groupNewStandardGroup({name: groupName, adminContactIds: contactIds.map(cid => BigInt(cid))});
            const result: { content: any, details: string; } = {
                content: [{type: "text", text: JSON.stringify(group.toJson())}],
                details: "Create group."
            };
            client.stop();
            return result;
        }
    },
    {
        name: "olvid_group_disband",
        label: "Olvid Group Disband",
        description: "Disband an Olvid group that you are member of.",
        parameters: Type.Object({olvidChannelAccountId: Type.Optional(Type.String()), groupId: Type.Number()}),
        async execute(_id: string, params: unknown) {
            const client = getOlvidClient((params as {olvidChannelAccountId: string}).olvidChannelAccountId);
            const groupId: number = (params as {groupId: number}).groupId;
            const ret = await client.groupDisband({groupId: BigInt(groupId)});
            const result: { content: any, details: string; } = {
                content: [{type: "text", text: JSON.stringify(ret)}],
                details: "Result of GroupDisband method."
            };
            client.stop();
            return result;

        }
    },
    {
        name: "olvid_group_leave",
        label: "Olvid Group Leave",
        description: "Leaves an Olvid group that you’re a member of. The group remains for others, but you cease to see its updates.",
        parameters: Type.Object({olvidChannelAccountId: Type.Optional(Type.String()), groupId: Type.Number()}),
        async execute(_id: string, params: unknown) {
            const client = getOlvidClient((params as {olvidChannelAccountId: string}).olvidChannelAccountId);
            const groupId: number = (params as {groupId: number}).groupId;
            const ret = await client.groupLeave({groupId: BigInt(groupId)})
            const result: { content: any, details: string; } = {
                content: [{type: "text", text: JSON.stringify(ret)}],
                details: "Result of GroupLeave method."
            };
            client.stop();
            return result;
        }
    }
]
