$(document).on('click', '.user_edit', function () {
    let user_id = $(this).closest('.row').data('user_id')
    console.log(user_id)
    $.ajax({
        url: '/admin/users',  // Обратите внимание на добавленный префикс /admin
        method: 'GET',
        data: {user_id: user_id},
        success: function (data) {
            $('#user_id').val(user_id)
            $('#username').val(data.username)
            $('#email').val(data.email)
            $('#role').val(data.role)
            $('#userModal').modal('show')
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.error("AJAX Error:", textStatus, errorThrown);
        }
    });
})

$('#userModal').on('hide.bs.modal', function () {
    $('#user_id').val('')
    $('#username').val('')
    $('#email').val('')
    $('#role').val('')
})