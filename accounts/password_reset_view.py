from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken
import logging

logger = logging.getLogger(__name__)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")
        logout_all = request.data.get("logout_all", False)

        if not old_password or not new_password:
            return Response(
                {"message": "Both old and new passwords are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user

        if not user.check_password(old_password):
            return Response(
                {"message": "Current password is incorrect"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_password(new_password, user)
        except ValidationError as e:
            return Response(
                {"message": " ".join(e.messages)}, status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()

        if logout_all:
            logger.error("Logging out from all devices")
            blacklist_all_user_tokens(user)

        return Response(
            {"message": "Password updated successfully"}, status=status.HTTP_200_OK
        )
        
        
def blacklist_all_user_tokens(user):
        """
        Blacklists all outstanding refresh tokens for a given user.
        """
        outstanding_tokens = OutstandingToken.objects.filter(user=user)
        for token_obj in outstanding_tokens:
            try:
                # Reconstruct RefreshToken object from the raw token
                refresh_token = RefreshToken(token_obj.token)
                refresh_token.blacklist()
            except Exception as e:
                print(f"Error blacklisting token {token_obj.token}: {e}")
        print(f"All tokens for user {user.username} have been blacklisted.")
