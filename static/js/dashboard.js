// ==========================================
// DASHBOARD
// ==========================================


document.addEventListener(
    "DOMContentLoaded",
    loadDashboard
);


async function loadDashboard() {

    try {

        const response =
            await fetch(
                "/api/dashboard"
            );


        if (!response.ok) {

            throw new Error(
                "Unable to load dashboard"
            );

        }


        const data =
            await response.json();


        document.getElementById(
            "poseCount"
        ).textContent =
            data.poseCount;


        document.getElementById(
            "analysisCount"
        ).textContent =
            data.analysisCount;


        document.getElementById(
            "averageScore"
        ).textContent =
            `${data.averageScore}%`;


        renderRecentAnalysis(
            data.recentAnalysis
        );

    }

    catch (error) {

        console.error(
            error
        );

    }

}


// ==========================================
// RECENT ANALYSIS
// ==========================================

function renderRecentAnalysis(
    analyses
) {

    const container =
        document.getElementById(
            "analysisList"
        );


    container.innerHTML = "";


    if (!analyses ||
        analyses.length === 0) {

        container.innerHTML = `

            <div class="empty-state">

                <h3>
                    No analysis yet
                </h3>

                <p>
                    Use the Yoga Analyzer
                    to create your first result.
                </p>

            </div>

        `;

        return;

    }


    analyses.forEach(
        function (item) {

            const element =
                document.createElement(
                    "div"
                );


            element.className =
                "analysis-item";


            element.innerHTML = `

                <div class="analysis-pose">
                    🧘
                </div>


                <div class="analysis-details">

                    <strong>
                        ${escapeHTML(
                            item.pose
                        )}
                    </strong>

                    <span>
                        Confidence:
                        ${item.confidence}%
                    </span>

                </div>


                <div class="analysis-score">

                    ${item.score}%

                </div>

            `;


            container.appendChild(
                element
            );

        }
    );

}


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