#!/bin/bash -x

#shell options 
set -e
# variables
api_url="$gitlab_api_url/api/v4/projects/$gitlabMergeRequestTargetProjectId/merge_requests/$gitlabMergeRequestIid"
nl_sep=" <br> "

#post comment to PR
post_pr_comment() {
    switch_set_e
    format_change_output output
    curl -s -X POST --header "PRIVATE-TOKEN: $GITLAB_SVC_ACCNT_TOKEN" -d "body=${stack_changes}" $api_url/notes
    switch_set_e
}

switch_set_e() {
set_state=$-
if [[ $set_state =~ e ]]; then 
    set +e
else 
    set -e
fi
}


#reads output file into a string, this is required to post a multiline comments
format_change_output () {
        stack_changes=""
        set +x
        while read -r LINE
        do
        LINE=$(sed -E 's/\\/\\\\/g' <<<"${LINE}") #escape \ 
        if [ "$repo_type" = "bitbucket" ] || [ "$repo_type" = "github" ] ; then
            stack_changes="${stack_changes} $nl_sep ${LINE//\"/\\\"}" #add esc char for " and append to string
        else
            stack_changes="${stack_changes} $nl_sep ${LINE}"
        fi
        done < $1
        set -x
        echo $stack_changes
}

exit_and_set_build_status() {
    echo "CODEBUILD_BUILD_SUCCEEDING=false" >> $WORKSPACE/variables_file
    exit 1
}

if [[ ! -z "$cloudfoundation_approved_users" ]]; then
    commented_user=`curl -s -X GET --header "PRIVATE-TOKEN: $GITLAB_SVC_ACCNT_TOKEN" $api_url/notes | jq -r '.[0].author.username'`
    if [[ "$cloudfoundation_approved_users" == *"$commented_user"* ]]; then
        echo "DEPLOY Operation requested by approved user: $commented_user"
    else
        echo "Authorization Error: DEPLOY Operation is requested by user $commented_user" > output
        echo "This user is not part of cloudfoundation_approved_users secret in Jenkins" >> output
        post_pr_comment
        exit_and_set_build_status
    fi
fi