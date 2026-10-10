// ==========================================
// YOGA POSE CRUD
// ==========================================


let poses = [];


// ==========================================
// DOM ELEMENTS
// ==========================================

const poseGrid =
    document.getElementById(
        "poseGrid"
    );


const poseModal =
    document.getElementById(
        "poseModal"
    );


const poseForm =
    document.getElementById(
        "poseForm"
    );


const openAddPoseBtn =
    document.getElementById(
        "openAddPoseBtn"
    );


const closePoseModal =
    document.getElementById(
        "closePoseModal"
    );


const cancelPoseBtn =
    document.getElementById(
        "cancelPoseBtn"
    );


const searchInput =
    document.getElementById(
        "poseSearch"
    );


const difficultyFilter =
    document.getElementById(
        "difficultyFilter"
    );


// ==========================================
// LOAD POSES
// READ OPERATION
// ==========================================

async function loadPoses() {

    try {

        const response =
            await fetch(
                "/api/poses"
            );


        if (!response.ok) {

            throw new Error(
                "Failed to load poses"
            );

        }


        poses =
            await response.json();


        renderPoses();

    }

    catch (error) {

        console.error(
            error
        );


        poseGrid.innerHTML = `

            <div class="empty-state">

                <h3>
                    Unable to load poses
                </h3>

                <p>
                    Please refresh the page.
                </p>

            </div>

        `;

    }

}


// ==========================================
// RENDER
// ==========================================

function renderPoses() {

    if (!poseGrid) {

        return;

    }


    const search =
        searchInput.value
            .trim()
            .toLowerCase();


    const difficulty =
        difficultyFilter.value;


    const filtered =
        poses.filter(
            function (pose) {

                const matchesSearch =

                    pose.name
                        .toLowerCase()
                        .includes(search)

                    ||

                    pose.englishName
                        .toLowerCase()
                        .includes(search);


                const matchesDifficulty =

                    difficulty === "all"

                    ||

                    pose.difficulty ===
                    difficulty;


                return (
                    matchesSearch &&
                    matchesDifficulty
                );

            }
        );


    poseGrid.innerHTML = "";


    if (filtered.length === 0) {

        poseGrid.innerHTML = `

            <div class="empty-state">

                <h3>
                    No poses found
                </h3>

                <p>
                    Try another search.
                </p>

            </div>

        `;

        return;

    }


    filtered.forEach(
        function (pose) {

            const card =
                createPoseCard(
                    pose
                );


            poseGrid.appendChild(
                card
            );

        }
    );

}


// ==========================================
// CREATE CARD
// ==========================================

function createPoseCard(
    pose
) {

    const card =
        document.createElement(
            "div"
        );


    card.className =
        "pose-card";


    card.innerHTML = `

        <div class="pose-card-image">

            🧘

        </div>


        <div class="pose-card-content">

            <h3>
                ${escapeHTML(pose.name)}
            </h3>

            <span class="english-name">

                ${escapeHTML(
                    pose.englishName
                )}

            </span>


            <p>

                ${escapeHTML(
                    pose.description
                )}

            </p>


            <div class="pose-meta">

                <span
                    class="difficulty
                    ${pose.difficulty.toLowerCase()}"
                >

                    ${escapeHTML(
                        pose.difficulty
                    )}

                </span>


                <div class="pose-actions">

                    <button
                        class="icon-btn"
                        onclick="editPose(${pose.id})"
                        title="Edit"
                    >
                        ✏
                    </button>


                    <button
                        class="icon-btn delete"
                        onclick="deletePose(${pose.id})"
                        title="Delete"
                    >
                        🗑
                    </button>

                </div>

            </div>

        </div>

    `;


    return card;

}


// ==========================================
// OPEN ADD MODAL
// ==========================================

openAddPoseBtn.addEventListener(
    "click",
    function () {

        openAddModal();

    }
);


function openAddModal() {

    poseForm.reset();


    document.getElementById(
        "poseId"
    ).value = "";


    document.getElementById(
        "modalTitle"
    ).textContent =
        "Add Yoga Pose";


    clearValidation();


    poseModal.classList.add(
        "show"
    );

}


// ==========================================
// CLOSE MODAL
// ==========================================

function closeModal() {

    poseModal.classList.remove(
        "show"
    );

}


closePoseModal.addEventListener(
    "click",
    closeModal
);


cancelPoseBtn.addEventListener(
    "click",
    closeModal
);


// ==========================================
// FORM SUBMIT
// CREATE / UPDATE
// ==========================================

poseForm.addEventListener(
    "submit",
    async function (event) {

        event.preventDefault();


        // JavaScript validation
        const isValid =
            validateForm();


        if (!isValid) {

            return;

        }


        const id =
            document.getElementById(
                "poseId"
            ).value;


        const data = {

            name:
                document.getElementById(
                    "poseName"
                ).value.trim(),

            englishName:
                document.getElementById(
                    "poseEnglishName"
                ).value.trim(),

            difficulty:
                document.getElementById(
                    "poseDifficulty"
                ).value,

            duration:
                document.getElementById(
                    "poseDuration"
                ).value.trim(),

            benefits:
                document.getElementById(
                    "poseBenefits"
                ).value.trim(),

            description:
                document.getElementById(
                    "poseDescription"
                ).value.trim()

        };


        try {

            let response;


            // ==================================
            // UPDATE
            // ==================================

            if (id) {

                response =
                    await fetch(
                        `/api/poses/${id}`,
                        {

                            method:
                                "PUT",

                            headers: {

                                "Content-Type":
                                    "application/json"

                            },

                            body:
                                JSON.stringify(
                                    data
                                )

                        }
                    );

            }


            // ==================================
            // CREATE
            // ==================================

            else {

                response =
                    await fetch(
                        "/api/poses",
                        {

                            method:
                                "POST",

                            headers: {

                                "Content-Type":
                                    "application/json"

                            },

                            body:
                                JSON.stringify(
                                    data
                                )

                        }
                    );

            }


            const result =
                await response.json();


            if (!response.ok) {

                throw new Error(
                    result.error ||
                    "Operation failed"
                );

            }


            showNotification(
                result.message ||
                "Operation successful"
            );


            closeModal();


            await loadPoses();

        }

        catch (error) {

            console.error(
                error
            );


            showNotification(
                error.message,
                "error"
            );

        }

    }
);


// ==========================================
// JAVASCRIPT FORM VALIDATION
// ==========================================

function validateForm() {

    clearValidation();


    let valid = true;


    const name =
        document.getElementById(
            "poseName"
        ).value.trim();


    const englishName =
        document.getElementById(
            "poseEnglishName"
        ).value.trim();


    const difficulty =
        document.getElementById(
            "poseDifficulty"
        ).value;


    const duration =
        document.getElementById(
            "poseDuration"
        ).value.trim();


    const benefits =
        document.getElementById(
            "poseBenefits"
        ).value.trim();


    const description =
        document.getElementById(
            "poseDescription"
        ).value.trim();


    // ==================================
    // NAME
    // ==================================

    if (name === "") {

        showFieldError(
            "poseName",
            "Pose name is required."
        );

        valid = false;

    }

    else if (name.length < 3) {

        showFieldError(
            "poseName",
            "Pose name must contain at least 3 characters."
        );

        valid = false;

    }

    else if (name.length > 100) {

        showFieldError(
            "poseName",
            "Pose name cannot exceed 100 characters."
        );

        valid = false;

    }


    // ==================================
    // ENGLISH NAME
    // ==================================

    if (englishName === "") {

        showFieldError(
            "poseEnglishName",
            "English name is required."
        );

        valid = false;

    }

    else if (englishName.length < 3) {

        showFieldError(
            "poseEnglishName",
            "English name must contain at least 3 characters."
        );

        valid = false;

    }


    // ==================================
    // DIFFICULTY
    // ==================================

    if (difficulty === "") {

        showFieldError(
            "poseDifficulty",
            "Please select a difficulty."
        );

        valid = false;

    }


    // ==================================
    // DURATION
    // ==================================

    if (duration === "") {

        showFieldError(
            "poseDuration",
            "Duration is required."
        );

        valid = false;

    }

    else if (duration.length > 50) {

        showFieldError(
            "poseDuration",
            "Duration cannot exceed 50 characters."
        );

        valid = false;

    }


    // ==================================
    // BENEFITS
    // ==================================

    if (benefits === "") {

        showFieldError(
            "poseBenefits",
            "Benefits are required."
        );

        valid = false;

    }

    else if (benefits.length < 10) {

        showFieldError(
            "poseBenefits",
            "Please enter at least 10 characters."
        );

        valid = false;

    }


    // ==================================
    // DESCRIPTION
    // ==================================

    if (description === "") {

        showFieldError(
            "poseDescription",
            "Description is required."
        );

        valid = false;

    }

    else if (description.length < 10) {

        showFieldError(
            "poseDescription",
            "Please enter at least 10 characters."
        );

        valid = false;

    }


    return valid;

}


// ==========================================
// SHOW VALIDATION ERROR
// ==========================================

function showFieldError(
    fieldId,
    message
) {

    const field =
        document.getElementById(
            fieldId
        );


    const error =
        document.getElementById(
            fieldId + "Error"
        );


    field.classList.add(
        "input-error"
    );


    error.textContent =
        message;

}


// ==========================================
// CLEAR VALIDATION
// ==========================================

function clearValidation() {

    document
        .querySelectorAll(
            ".validation-error"
        )
        .forEach(
            function (element) {

                element.textContent = "";

            }
        );


    document
        .querySelectorAll(
            ".input-error"
        )
        .forEach(
            function (element) {

                element.classList.remove(
                    "input-error"
                );

            }
        );

}


// ==========================================
// EDIT
// UPDATE OPERATION
// ==========================================

async function editPose(
    id
) {

    try {

        const response =
            await fetch(
                `/api/poses/${id}`
            );


        const pose =
            await response.json();


        if (!response.ok) {

            throw new Error(
                pose.error
            );

        }


        document.getElementById(
            "poseId"
        ).value =
            pose.id;


        document.getElementById(
            "poseName"
        ).value =
            pose.name;


        document.getElementById(
            "poseEnglishName"
        ).value =
            pose.englishName;


        document.getElementById(
            "poseDifficulty"
        ).value =
            pose.difficulty;


        document.getElementById(
            "poseDuration"
        ).value =
            pose.duration;


        document.getElementById(
            "poseBenefits"
        ).value =
            pose.benefits;


        document.getElementById(
            "poseDescription"
        ).value =
            pose.description;


        document.getElementById(
            "modalTitle"
        ).textContent =
            "Edit Yoga Pose";


        clearValidation();


        poseModal.classList.add(
            "show"
        );

    }

    catch (error) {

        showNotification(
            error.message,
            "error"
        );

    }

}


// ==========================================
// DELETE
// DELETE OPERATION
// ==========================================

async function deletePose(
    id
) {

    const pose =
        poses.find(
            function (item) {

                return item.id === id;

            }
        );


    if (!pose) {

        return;

    }


    const confirmed =
        confirm(
            `Are you sure you want to delete ${pose.name}?`
        );


    if (!confirmed) {

        return;

    }


    try {

        const response =
            await fetch(
                `/api/poses/${id}`,
                {

                    method:
                        "DELETE"

                }
            );


        const result =
            await response.json();


        if (!response.ok) {

            throw new Error(
                result.error
            );

        }


        showNotification(
            result.message
        );


        await loadPoses();

    }

    catch (error) {

        showNotification(
            error.message,
            "error"
        );

    }

}


// ==========================================
// SEARCH
// ==========================================

searchInput.addEventListener(
    "input",
    renderPoses
);


// ==========================================
// FILTER
// ==========================================

difficultyFilter.addEventListener(
    "change",
    renderPoses
);


// ==========================================
// HTML ESCAPE
// ==========================================

function escapeHTML(
    value
) {

    const div =
        document.createElement(
            "div"
        );


    div.textContent =
        value;


    return div.innerHTML;

}


// ==========================================
// INITIALIZE
// ==========================================

loadPoses();